#!/usr/bin/env python3
"""
Interop test: driving a PyScotch Dgraph from an mpi4py communicator.

Unlike the other scripts here (which use the bundled zero-dependency
pyscotch.mpi wrapper), this one hands mpi4py communicators straight to
Dgraph(comm=...). It exercises three things the interop must get right:

  1. Dgraph(comm=MPI.COMM_WORLD) — the native MPI_Comm handle mpi4py exposes
     via MPI._handleof must be exactly what SCOTCH_dgraphInit expects.
  2. A genuine subset communicator (MPI.Split) — proves arbitrary comms work,
     not just COMM_WORLD, and that each subgroup runs PT-Scotch independently.
  3. coarsen() propagates the mpi4py communicator to the coarse Dgraph.

Run with: mpirun -np 4 python dgraph_mpi4py_interop.py
"""

import sys
from pathlib import Path

# Add pyscotch to path for development (repo root)
sys.path.insert(0, str(Path(__file__).parents[3]))

from mpi4py import MPI  # noqa: E402  (import after sys.path tweak; runs MPI_Init)

from pyscotch.dgraph import Dgraph  # noqa: E402


def main():
    world = MPI.COMM_WORLD
    wrank, wsize = world.Get_rank(), world.Get_size()

    # --- 1. COMM_WORLD: build a distributed 3D grid, check, partition ---------
    dg = Dgraph(comm=world)
    dg.build_grid_3d(8, 8, 8, baseval=0)
    if not dg.check():
        print(f"FAIL: dgraphCheck failed on COMM_WORLD (rank {wrank})")
        dg.exit()
        return 1
    d = dg.data(want_vertglbnbr=True, want_vertlocnbr=True)
    assert d["vertglbnbr"] == 8 * 8 * 8, d
    # The graph's own rank accessor must agree with mpi4py's.
    assert dg._comm_rank() == wrank, (dg._comm_rank(), wrank)
    part = dg.part(4)
    assert len(part) == d["vertlocnbr"], (len(part), d["vertlocnbr"])
    assert part.min() >= 0 and part.max() < 4, (int(part.min()), int(part.max()))
    dg.exit()

    # --- 2. coarsen() must carry the mpi4py comm to the coarse graph ----------
    dg2 = Dgraph(comm=world)
    dg2.build_grid_3d(8, 8, 8, baseval=0)
    coarse, mult = dg2.coarsen(0.8)
    assert coarse._mpi4py_comm is world, "coarsen did not propagate the mpi4py comm"
    if mult is not None:
        coarse.exit()
    dg2.exit()

    # --- 3. A real subset communicator (Split) runs PT-Scotch independently ---
    color = wrank % 2
    sub = world.Split(color=color, key=wrank)
    dg3 = Dgraph(comm=sub)
    dg3.build_grid_3d(4, 4, 4, baseval=0)
    assert dg3.check(), "dgraphCheck failed on Split() subgroup"
    assert dg3._comm_rank() == sub.Get_rank()
    ds = dg3.data(want_vertglbnbr=True)
    assert ds["vertglbnbr"] == 4 * 4 * 4, ds
    dg3.exit()
    sub.Free()

    world.Barrier()
    if wrank == 0:
        print(f"PASS: mpi4py interop across {wsize} processes")
    # Return normally: mpi4py registers an atexit handler that calls
    # MPI_Finalize. Skipping it (e.g. os._exit) makes OpenMPI 5 report an
    # abnormal termination, so let the interpreter shut down cleanly.
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # pragma: no cover - surfaced through mpirun output
        rank = MPI.COMM_WORLD.Get_rank()
        print(f"ERROR on rank {rank}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
