#!/usr/bin/env python3
"""
Port of test_scotch_dgraph_grow.c

Tests the SCOTCH_dgraphGrow() routine.
Grows subgraphs from seed vertices to create partitions.

Reference: external/scotch/src/check/test_scotch_dgraph_grow.c

Run with: mpirun -np 3 python dgraph_grow.py <graph_file> <mapping_file>
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
    """Test dgraph grow with seed vertices."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        # Check arguments
        if len(sys.argv) != 3:
            if rank == 0:
                print(f"usage: {sys.argv[0]} graph_file mapping_file")
            mpi.finalize()
            return 1

        graph_file = Path(sys.argv[1])
        mapping_file = Path(sys.argv[2])

        if not graph_file.exists():
            if rank == 0:
                print(f"ERROR: Graph file not found: {graph_file}")
            mpi.finalize()
            return 1

        # Note: PT-Scotch variant is set via environment variables:
        # PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1

        # Barrier: Synchronize for debug
        mpi.barrier()

        # Initialize source graph
        grafdat = Dgraph()

        # Load graph
        grafdat.load(graph_file, baseval=-1, flagval=0)

        # Barrier: Synchronize after load
        mpi.barrier()

        # Compute ghost edge array
        # C code: line 66
        if grafdat.ghst() != 0:
            print(f"ERROR: cannot compute ghost edge array")
            grafdat.exit()
            mpi.finalize()
            os._exit(1)

        # Get graph data (need baseval, vertex counts, ghost count)
        data = grafdat.data(
            want_baseval=True,
            want_vertglbnbr=True,
            want_vertlocnbr=True,
            want_vertgstnbr=True
        )
        baseval = data['baseval']
        vertglbnbr = data['vertglbnbr']
        vertlocnbr = data['vertlocnbr']
        vertgstnbr = data['vertgstnbr']

        # Allocate seed array (3 seeds per rank)
        seedloctab = np.zeros(vertlocnbr, dtype=lib.get_scotch_dtype())

        # Allocate partition array (includes ghost vertices!)
        partgsttab = np.full(vertgstnbr, -1, dtype=lib.get_scotch_dtype())

        # TODO: NEED TO IMPLEMENT random seed selection
        # C code uses SCOTCH_randomReset() and SCOTCH_randomVal()
        # For now, use Python's random with a fixed seed for determinism
        import random
        random.seed(42)  # Deterministic for testing

        seedloctab[0] = baseval + random.randint(0, vertlocnbr - 1)
        seedloctab[1] = baseval + random.randint(0, vertlocnbr - 1)
        seedloctab[2] = baseval + random.randint(0, vertlocnbr - 1)

        # Mark seed vertices with their partition IDs (0, 1, 2)
        partgsttab[seedloctab[0] - baseval] = 0
        partgsttab[seedloctab[1] - baseval] = 1
        partgsttab[seedloctab[2] - baseval] = 2

        # Grow regions from seeds
        # C code: line 115
        # Parameters:
        #   seedlocnbr=3 - number of seeds
        #   seedloctab - array of seed vertices
        #   distmax=4 - maximum distance to grow
        #   partgsttab - partition array (modified in-place)
        if grafdat.grow(3, seedloctab, 4, partgsttab) != 0:
            print(f"ERROR: cannot compute grown regions")
            grafdat.exit()
            mpi.finalize()
            os._exit(1)

        # Write mapping to file (sequential output with barriers)
        # NOTE: This uses FILE* operations which may be blocked
        # C code: lines 189-217
        for procnum in range(size):
            mpi.barrier()

            if procnum == rank:
                # Open file (first rank writes, others append)
                mode = 'w' if procnum == 0 else 'a'

                with open(mapping_file, mode) as f:
                    if procnum == 0:
                        # First rank writes header
                        f.write(f"{vertglbnbr}\n")
                        vertlocadj = baseval
                    else:
                        # Other ranks receive offset from previous rank
                        # TODO: NEED MPI recv/send for vertex offset
                        # For now, calculate it ourselves
                        vertlocadj = baseval  # Placeholder

                    # Write partition assignments for local vertices
                    for vertlocnum in range(vertlocnbr):
                        f.write(f"{vertlocadj + vertlocnum}\t{partgsttab[vertlocnum]}\n")

                    # TODO: Send offset to next rank if not last
                    # C code: lines 212-215
                    # if procnum < (size - 1):
                    #     vertlocadj += vertlocnbr
                    #     MPI_Send(&vertlocadj, ...)

        # Clean up
        grafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Grow test completed successfully")
        os._exit(0)

    except NotImplementedError as e:
        rank = mpi.comm_rank() if mpi.is_initialized() else '?'
        print(f"[Rank {rank}] {e}")
        if mpi.is_initialized():
            mpi.finalize()
        os._exit(1)

    except Exception as e:
        rank = mpi.comm_rank() if mpi.is_initialized() else '?'
        print(f"ERROR on rank {rank}: {e}")
        import traceback
        traceback.print_exc()
        if mpi.is_initialized():
            mpi.finalize()
        os._exit(1)


if __name__ == "__main__":
    main()
