#!/usr/bin/env python3
"""
Port of test_scotch_dgraph_check.c - loads and validates real graphs.
Run with: mpirun -np 2 python dgraph_check_real.py <graph_file>
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, '/home/sharl/personal_gits/pyscotch')

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph

def main():
    """Test dgraph check with real graph file."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        if len(sys.argv) != 2:
            if rank == 0:
                print(f"usage: {sys.argv[0]} graph_file")
            mpi.finalize()
            return 1

        graph_file = Path(sys.argv[1])
        
        if rank == 0:
            print(f"Loading and checking graph: {graph_file}")
            if not graph_file.exists():
                print(f"ERROR: Graph file not found: {graph_file}")
                mpi.finalize()
                return 1

        # Note: PT-Scotch variant is set via environment variables:
        # PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1

        # Initialize dgraph
        dgraph = Dgraph()
        
        # Load graph from file (like Scotch's test does)
        dgraph.load(graph_file, baseval=-1, flagval=0)

        # Check the dgraph
        is_valid = dgraph.check()

        if not is_valid:
            if rank == 0:
                print("FAIL: Graph check failed")
            dgraph.exit()
            mpi.finalize()
            import os
            os._exit(1)

        if rank == 0:
            print("PASS: Graph check successful")

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
