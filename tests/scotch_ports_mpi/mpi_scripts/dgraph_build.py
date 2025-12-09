#!/usr/bin/env python3
"""
Standalone MPI script to test SCOTCH_dgraphBuild.
Run with: mpirun -np 2 python dgraph_build.py
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
    """Test dgraph build."""
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
            print(f"Running dgraph_build with {size} MPI processes")

        # Note: PT-Scotch variant is set via environment variables:
        # PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1
        dtype = lib.get_dtype()

        # Create a simple distributed graph: each process has 2 vertices
        # Rank 0: vertices 0, 1
        # Rank 1: vertices 2, 3
        # Edges: 0-1, 1-2, 2-3 (cross-process edge between 1-2)

        if rank == 0:
            # Rank 0 has vertices 0, 1
            # Vertex 0: edges to [1]
            # Vertex 1: edges to [2] (remote)
            vertloctab = np.array([0, 1, 2], dtype=dtype)
            edgeloctab = np.array([1, 2], dtype=dtype)  # local vertex 1, remote vertex 2
        else:  # rank == 1
            # Rank 1 has vertices 2, 3
            # Vertex 2: edges to [1] (remote), [3]
            # Vertex 3: edges to [2]
            vertloctab = np.array([0, 2, 3], dtype=dtype)
            edgeloctab = np.array([1, 3, 2], dtype=dtype)  # remote 1, local 3, then local 2

        baseval = 0

        # Build the dgraph
        dgraph = Dgraph()
        dgraph.build(
            vertloctab=vertloctab,
            edgeloctab=edgeloctab,
            baseval=baseval
        )

        if rank == 0:
            print("PASS: Dgraph build successful")

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
