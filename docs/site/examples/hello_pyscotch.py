#!/usr/bin/env python3
"""PyScotch hello-world — works with the sequential build and the parallel one.

Sequential (any install):
    python hello_pyscotch.py

Parallel (needs a PT-Scotch build + mpi4py). PYSCOTCH_PARALLEL must be set
*before* pyscotch is imported, so put it on the command line:
    PYSCOTCH_PARALLEL=1 PYSCOTCH_INT_SIZE=64 mpirun -n 2 python hello_pyscotch.py

The sequential section always runs. The parallel section runs only when
PYSCOTCH_PARALLEL=1 is set; otherwise it says exactly what is missing.
Exit code is 0 on success, 1 on failure.
"""

import os
import sys

# Read this BEFORE importing pyscotch: the binding picks the sequential or the
# parallel library at import time, so setting it later would have no effect.
WANT_PARALLEL = os.environ.get("PYSCOTCH_PARALLEL") == "1"

import numpy as np  # noqa: E402

try:
    import pyscotch  # noqa: E402
    from pyscotch import Graph, get_scotch_dtype, random_reset, scotch_version  # noqa: E402
    from pyscotch.libscotch import is_parallel  # noqa: E402
except FileNotFoundError as exc:
    # With PYSCOTCH_PARALLEL=1, pyscotch loads libptscotch.so *at import* and
    # raises here if the install is sequential-only. Explain instead of dumping
    # a traceback — this is the most common parallel setup mistake.
    if WANT_PARALLEL and "libptscotch" in str(exc):
        print("PYSCOTCH_PARALLEL=1 was set, but this install has no PT-Scotch:")
        print(f"    {exc}")
        print("\nThis install is sequential-only. Either drop PYSCOTCH_PARALLEL=1 to")
        print("run the sequential demo, or install a parallel Scotch, e.g.:")
        print("    pyscotch scotch build 7.0.11 --parallel --use")
        sys.exit(1)
    raise


def show_environment():
    print("=" * 62)
    print("PyScotch hello-world")
    print("=" * 62)
    print(f"  pyscotch version : {pyscotch.__version__}")
    print(f"  Scotch version   : {'.'.join(map(str, scotch_version()))}")
    print(f"  integer width    : {pyscotch.get_scotch_int_size()}-bit")
    # is_parallel() reports what the *loaded library* can do; PYSCOTCH_PARALLEL
    # only says what was asked for. They disagree on a sequential-only install.
    print(f"  PT-Scotch loaded : {is_parallel()}")
    print(f"  parallel wanted  : {WANT_PARALLEL}")
    print()


def hello_sequential():
    """Partition and order a small ring graph. Uses only the sequential API."""
    print("-- sequential ------------------------------------------------")

    # A 6-vertex ring: 0-1-2-3-4-5-0. Scotch wants an adjacency (CSR-like)
    # layout: verttab holds the start offset of each vertex's edge list,
    # edgetab holds the concatenated neighbour lists.
    dtype = get_scotch_dtype()  # int32 or int64, matching the loaded library
    verttab = np.array([0, 2, 4, 6, 8, 10, 12], dtype=dtype)
    edgetab = np.array([1, 5, 0, 2, 1, 3, 2, 4, 3, 5, 4, 0], dtype=dtype)

    g = Graph()
    g.build(verttab, edgetab)

    if not g.check():
        print("  FAILED: graph consistency check rejected the ring")
        return False
    nvert, nedge = g.size()
    print(f"  built ring graph : {nvert} vertices, {nedge} edges (check OK)")

    # Partitioning is randomized; reset the generator so runs are reproducible.
    random_reset()
    part = g.partition(2)
    sizes = np.bincount(part, minlength=2)
    print(f"  partition(2)     : {part.tolist()}  -> sizes {sizes.tolist()}")
    if set(part.tolist()) != {0, 1}:
        print(f"  FAILED: expected both parts to be used, got {set(part.tolist())}")
        return False

    random_reset()
    permtab, peritab = g.order()
    print(f"  order() perm     : {permtab.tolist()}")
    # permtab and peritab must be inverse permutations of each other.
    if not np.array_equal(peritab[permtab], np.arange(nvert)):
        print("  FAILED: order() permutation and its inverse are inconsistent")
        return False
    print("  order()          : permutation/inverse consistent")

    print("  sequential OK")
    return True


def mpi_rank():
    """This process's MPI rank, or 0 when not running under mpirun."""
    if not WANT_PARALLEL:
        return 0
    try:
        from mpi4py import MPI

        return MPI.COMM_WORLD.Get_rank()
    except ImportError:
        return 0


def hello_parallel():
    """Distribute a 3D grid across MPI ranks and partition it with PT-Scotch."""
    if mpi_rank() == 0:
        print("-- parallel --------------------------------------------------")

    if not WANT_PARALLEL:
        print("  skipped: PYSCOTCH_PARALLEL=1 is not set.")
        print(f"  This install {'has' if is_parallel() else 'does NOT have'} PT-Scotch loaded.")
        print("  To run the parallel section you need a PT-Scotch build + mpi4py:")
        print("      pip install mpi4py")
        print("      PYSCOTCH_PARALLEL=1 PYSCOTCH_INT_SIZE=64 \\")
        print("          mpirun -n 2 python hello_pyscotch.py")
        return True  # not a failure — just not requested

    # A sequential-only install never reaches this point: with PYSCOTCH_PARALLEL=1
    # the import above already failed. So if we are here, PT-Scotch really loaded.
    assert is_parallel(), "PYSCOTCH_PARALLEL=1 imported cleanly but PT-Scotch is absent"

    try:
        from mpi4py import MPI
    except ImportError:
        print("  FAILED: PYSCOTCH_PARALLEL=1 but mpi4py is not installed (pip install mpi4py)")
        return False

    from pyscotch import Dgraph

    comm = MPI.COMM_WORLD
    rank, nranks = comm.Get_rank(), comm.Get_size()

    try:
        dg = Dgraph(comm=comm)
    except RuntimeError as exc:
        # Raised when the loaded library has no PT-Scotch support.
        if rank == 0:
            print(f"  FAILED: {exc}")
        return False

    # Each rank holds a slice of a 6x6x6 grid; Scotch handles the distribution.
    dg.build_grid_3d(6, 6, 6)
    if not dg.check():
        if rank == 0:
            print("  FAILED: distributed grid failed its consistency check")
        return False

    nparts = 3
    part = dg.part(nparts)

    # Each rank only sees its own slice, so reduce to describe the whole graph.
    local_counts = np.bincount(part, minlength=nparts)
    total_counts = comm.allreduce(local_counts, op=MPI.SUM)
    local_vertices = len(part)
    total_vertices = comm.allreduce(local_vertices, op=MPI.SUM)
    dg.exit()

    ok = True
    if part.size and (part.min() < 0 or part.max() >= nparts):
        print(f"  FAILED (rank {rank}): part values out of range [0,{nparts})")
        ok = False
    ok = comm.allreduce(ok, op=MPI.LAND)

    comm.Barrier()
    if rank == 0:
        print(f"  ranks            : {nranks}")
        print(f"  6x6x6 grid       : {total_vertices} vertices total (check OK)")
        print(f"  part({nparts})          : sizes {total_counts.tolist()}")
        if total_vertices != 216:
            print(f"  FAILED: expected 216 vertices, got {total_vertices}")
            ok = False
        print("  parallel OK" if ok else "  parallel FAILED")
    return ok


def main():
    # Under mpirun every rank runs this file. The banner and the sequential
    # demo are purely local, so only rank 0 does them — otherwise the output is
    # repeated once per rank. The parallel demo is collective: all ranks join.
    rank = mpi_rank()
    results = []
    if rank == 0:
        show_environment()
        results.append(hello_sequential())
        print()

    results.append(hello_parallel())

    if rank == 0:
        print()
        print("=" * 62)
        print("ALL OK" if all(results) else "FAILURES — see above")
        print("=" * 62)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
