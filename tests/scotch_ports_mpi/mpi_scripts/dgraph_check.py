#!/usr/bin/env python3
"""
Standalone MPI script to test SCOTCH_dgraphCheck.
Run with: mpirun -np 2 python dgraph_check.py
"""
import sys
import numpy as np
from ctypes import byref

# Add parent directory to path
sys.path.insert(0, '/home/sharl/personal_gits/pyscotch')

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph

def main():
    """Test dgraph check."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        if size != 2:
            if rank == 0:
                print(f"ERROR: This test requires exactly 2 MPI processes, got {size}")
            mpi.finalize()
            return 1

        if rank == 0:
            print(f"Running dgraph_check with {size} MPI processes")

        # Note: PT-Scotch variant is set via environment variables:
        # PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1
        dtype = lib.get_dtype()

        # Create a simple distributed graph with NO edges
        # This is the simplest valid distributed graph for testing
        # Each process has 2 vertices with no connections
        # NOTE: Graphs with edges require ghost edge arrays (edgegsttab)
        # which properly map cross-process edges. For now, test with empty graph.
        vertloctab = np.array([0, 0, 0], dtype=dtype)  # 2 vertices, 0 edges
        edgeloctab = np.array([], dtype=dtype)  # Empty edge array

        baseval = 0

        # Build the dgraph
        dgraph = Dgraph()
        dgraph.build(
            vertloctab=vertloctab,
            edgeloctab=edgeloctab,
            baseval=baseval
        )

        # Check the dgraph
        is_valid = dgraph.check()

        if not is_valid:
            if rank == 0:
                print("FAIL: Dgraph check failed")
            dgraph.exit()  # Cleanup before MPI finalize
            mpi.finalize()
            import os
            os._exit(1)

        if rank == 0:
            print("PASS: Dgraph check successful")

        # Cleanup dgraph before finalizing MPI
        dgraph.exit()

        # Finalize MPI
        mpi.finalize()

        # Exit immediately to avoid Python cleanup issues
        import os
        os._exit(0)

    except Exception as e:
        rank = mpi.comm_rank() if mpi.is_initialized() else '?'
        print(f"ERROR on rank {rank}: {e}")
        import traceback
        traceback.print_exc()
        if mpi.is_initialized():
            mpi.finalize()
        return 1

if __name__ == "__main__":
    sys.exit(main())
