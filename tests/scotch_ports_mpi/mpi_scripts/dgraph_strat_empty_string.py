#!/usr/bin/env python3
"""
Test that set_dgraph_mapping("") / set_dgraph_ordering("") select PT-Scotch's
default strategy, mirroring the sequential set_mapping/set_ordering setters.

At the raw C level, parsing "" installs a do-nothing method: partitioning puts
every vertex in part 0 and ordering returns the identity permutation, because
SCOTCH_dgraphMapCompute / SCOTCH_dgraphOrderCompute only build the real
default strategy when the inner Strat pointer is still NULL (a parsed "" is a
non-NULL empty strategy). PyScotch maps "" to reset-to-default so that ""
means "default" across the whole Strategy API. There is no upstream C test for
this; the structure mirrors the dgraph_part.py port (per-rank output
aggregated through a shared file with barriers). All collective operations run
before the rank-0 assertions so a failed assertion cannot deadlock the other
ranks in a later collective call.

Run with: mpirun -np 2 python dgraph_strat_empty_string.py <graph_file> <output_file>
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph
from pyscotch.strategy import Strategy

NPARTS = 4


def _aggregate(output_file, values, rank, size, vertglbnbr):
    """Write per-rank values to a shared file in rank order; load on rank 0."""
    for procnum in range(size):
        mpi.barrier()
        if procnum == rank:
            mode = "w" if procnum == 0 else "a"
            with open(output_file, mode) as f:
                for value in values:
                    f.write(f"{value}\n")
    mpi.barrier()
    if rank != 0:
        return None
    data = np.loadtxt(output_file, dtype=np.int64, ndmin=1)
    assert len(data) == vertglbnbr, f"expected {vertglbnbr} values, got {len(data)}"
    return data


def main():
    """Test that empty-string dgraph strategies mean "default", not "do nothing"."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        # Check arguments
        if len(sys.argv) != 3:
            if rank == 0:
                print(f"usage: {sys.argv[0]} graph_file output_file")
            mpi.finalize()
            return 1

        graph_file = Path(sys.argv[1])
        output_file = Path(sys.argv[2])

        if not graph_file.exists():
            if rank == 0:
                print(f"ERROR: Graph file not found: {graph_file}")
            mpi.finalize()
            return 1

        lib.SCOTCH_randomReset()

        # Barrier: Synchronize for debug
        mpi.barrier()

        # Initialize and load source graph
        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        mpi.barrier()

        data = grafdat.data(want_vertglbnbr=True, want_vertlocnbr=True)
        vertglbnbr = data["vertglbnbr"]
        vertlocnbr = data["vertlocnbr"]

        # --- Compute (collective) phase: no assertions between collectives ---

        # Partition with an empty-string mapping strategy.
        stratdat = Strategy()
        stratdat.set_dgraph_mapping("")
        partloctab = grafdat.part(NPARTS, stratdat)

        # Ordering with the default strategy (precondition control: the
        # default must reorder this graph, or the non-identity assertion on
        # the empty-string result proves nothing).
        dorddat0 = grafdat.order_init()
        grafdat.order_compute(dorddat0)
        permloctab0 = grafdat.order_perm(dorddat0)
        grafdat.order_exit(dorddat0)

        # Ordering with an empty-string ordering strategy.
        stratdat2 = Strategy()
        stratdat2.set_dgraph_ordering("")
        dorddat = grafdat.order_init()
        grafdat.order_compute(dorddat, stratdat2)
        permloctab = grafdat.order_perm(dorddat)
        grafdat.order_exit(dorddat)

        # Aggregate everything (barrier-sequenced shared files).
        parts = _aggregate(output_file, partloctab, rank, size, vertglbnbr)
        perm_default = _aggregate(
            output_file.with_suffix(".dord"), permloctab0, rank, size, vertglbnbr
        )
        perm = _aggregate(
            output_file.with_suffix(".eord"), permloctab, rank, size, vertglbnbr
        )

        # --- Assertion phase: local checks, then global checks on rank 0 ---
        assert len(partloctab) == vertlocnbr, "partloctab has wrong length"
        assert np.all(partloctab >= 0) and np.all(partloctab < NPARTS), (
            f"invalid part values on rank {rank}: "
            f"min={partloctab.min()}, max={partloctab.max()}"
        )

        if rank == 0:
            counts = np.bincount(parts, minlength=NPARTS)
            assert np.all(counts > 0), (
                f"empty part(s) with set_dgraph_mapping(''): counts={counts.tolist()} "
                "— the empty string installed a do-nothing method instead of the default"
            )

            assert not np.array_equal(perm_default, np.arange(vertglbnbr)), (
                "precondition: the default ordering must reorder, "
                "or this test proves nothing"
            )
            assert np.array_equal(np.sort(perm), np.arange(vertglbnbr)), (
                "set_dgraph_ordering('') produced an invalid permutation"
            )
            assert not np.array_equal(perm, np.arange(vertglbnbr)), (
                "set_dgraph_ordering('') returned the identity permutation "
                "— the empty string installed a do-nothing method instead of "
                "the default"
            )

        # Clean up
        grafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Empty-string dgraph strategy test completed successfully")
        os._exit(0)

    except Exception as e:
        rank = mpi.comm_rank() if mpi.is_initialized() else "?"
        print(f"ERROR on rank {rank}: {e}")
        import traceback

        traceback.print_exc()
        if mpi.is_initialized():
            mpi.finalize()
        os._exit(1)


if __name__ == "__main__":
    main()
