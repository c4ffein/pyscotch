#!/usr/bin/env python3
"""
Test for the remaining distributed ordering routines:
SCOTCH_dgraphOrderCompute(), SCOTCH_dgraphOrderPerm(),
SCOTCH_dgraphOrderCblkDist(), SCOTCH_dgraphOrderTreeDist(),
SCOTCH_dgraphOrderSave(), SCOTCH_dgraphOrderSaveMap(),
SCOTCH_dgraphOrderSaveTree().

Computes a distributed ordering, validates that the returned local
permutations form a global permutation, checks the distributed elimination
tree accessors, and saves the ordering in all three formats. The global
permutation is aggregated through a shared file with barriers, mirroring
the dgraph_band.py port structure.

Run with: mpirun -np 3 python dgraph_order_extra.py <graph_file> <output_file>
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


def main():
    """Test distributed ordering permutation, tree accessors and saving."""
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

        data = grafdat.data(want_baseval=True, want_vertglbnbr=True, want_vertlocnbr=True)
        baseval = data["baseval"]
        vertglbnbr = data["vertglbnbr"]
        vertlocnbr = data["vertlocnbr"]

        # --- High-level order(): local slice of a global permutation ---
        permloctab = grafdat.order()
        assert len(permloctab) == vertlocnbr, "permloctab has wrong length"

        # Aggregate permutation values through a shared file (barrier-
        # sequenced), then validate on rank 0 that they form a permutation.
        for procnum in range(size):
            mpi.barrier()
            if procnum == rank:
                mode = "w" if procnum == 0 else "a"
                with open(output_file, mode) as f:
                    for permval in permloctab:
                        f.write(f"{permval}\n")
        mpi.barrier()

        if rank == 0:
            perm = np.loadtxt(output_file, dtype=np.int64, ndmin=1)
            assert len(perm) == vertglbnbr, f"expected {vertglbnbr} values, got {len(perm)}"
            expected = np.arange(baseval, baseval + vertglbnbr, dtype=np.int64)
            assert np.array_equal(np.sort(perm), expected), "not a valid global permutation"

        # --- Explicit lifecycle: compute, tree accessors, saves ---
        dorddat = grafdat.order_init()
        grafdat.order_compute(dorddat)

        permloctab2 = grafdat.order_perm(dorddat)
        assert len(permloctab2) == vertlocnbr, "order_perm result has wrong length"
        assert np.all(permloctab2 >= baseval), "permutation values below base"
        assert np.all(permloctab2 < baseval + vertglbnbr), "permutation values out of range"

        cblkglbnbr = grafdat.order_cblk_dist(dorddat)
        assert cblkglbnbr >= 1, f"expected at least one column block, got {cblkglbnbr}"

        treeglbtab, sizeglbtab = grafdat.order_tree_dist(dorddat)
        assert len(treeglbtab) == cblkglbnbr and len(sizeglbtab) == cblkglbnbr
        assert np.all(sizeglbtab > 0), "column blocks must have positive sizes"
        assert int(sizeglbtab.max()) <= vertglbnbr, "column block larger than graph"
        # Father indices are either -1 (root) or valid column block indices
        assert np.all(treeglbtab >= -1) and np.all(treeglbtab < cblkglbnbr), "invalid tree"

        ord_file = output_file.with_suffix(".ord")
        map_file = output_file.with_suffix(".map")
        tree_file = output_file.with_suffix(".tree")
        grafdat.order_save(dorddat, ord_file)
        grafdat.order_save_map(dorddat, map_file)
        grafdat.order_save_tree(dorddat, tree_file)
        if rank == 0:
            for path in (ord_file, map_file, tree_file):
                assert path.exists() and path.stat().st_size > 0, f"empty save file: {path}"

        grafdat.order_exit(dorddat)

        # Clean up
        grafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Order extra test completed successfully")
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
