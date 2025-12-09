#!/usr/bin/env python3
"""
Standalone MPI script to test SCOTCH_dgraphInit.
Run with: mpirun -np 2 python dgraph_init.py
"""
import sys
from ctypes import byref

# Add parent directory to path
sys.path.insert(0, '/home/sharl/personal_gits/pyscotch')

from pyscotch import libscotch as lib
from pyscotch.libscotch import SCOTCH_Dgraph
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph

def main():
    """Test dgraph initialization."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        if rank == 0:
            print(f"Running with {size} MPI processes")

        # Note: PT-Scotch variant is set via environment variables:
        # PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1

        # Test 1: Initialize dgraph using low-level API
        dgraph = SCOTCH_Dgraph()
        comm = mpi.get_comm_world()
        ret = lib.SCOTCH_dgraphInit(byref(dgraph), comm)

        if ret != 0:
            if rank == 0:
                print(f"FAIL: SCOTCH_dgraphInit returned {ret}")
            mpi.finalize()
            return 1

        # Test 2: Exit dgraph (returns void)
        lib.SCOTCH_dgraphExit(byref(dgraph))

        # Test 3: Initialize using high-level Dgraph class
        dgraph_obj = Dgraph()

        if rank == 0:
            print("PASS: Dgraph initialization successful")

        # Cleanup dgraph before finalizing MPI
        dgraph_obj.exit()

        # Finalize MPI
        mpi.finalize()
        return 0

    except Exception as e:
        print(f"ERROR on rank {mpi.comm_rank() if mpi.is_initialized() else '?'}: {e}")
        if mpi.is_initialized():
            mpi.finalize()
        return 1

if __name__ == "__main__":
    sys.exit(main())
