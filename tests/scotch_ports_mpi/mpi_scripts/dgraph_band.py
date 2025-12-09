#!/usr/bin/env python3
"""
Port of test_scotch_dgraph_band.c

Tests the SCOTCH_dgraphBand() routine.
Extracts a band graph from a frontier.

Reference: external/scotch/src/check/test_scotch_dgraph_band.c

Run with: mpirun -np 3 python dgraph_band.py <graph_file> <mapping_file>
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
    """Test dgraph band extraction from frontier."""
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

        # Get graph data (need baseval and vertex counts)
        data = grafdat.data(
            want_baseval=True,
            want_vertglbnbr=True,
            want_vertlocnbr=True
        )
        baseval = data['baseval']
        vertglbnbr = data['vertglbnbr']
        vertlocnbr = data['vertlocnbr']

        # Allocate frontier array
        # C code: lines 156-159
        fronloctab = np.zeros(vertlocnbr, dtype=lib.get_scotch_dtype())

        # Initialize band graph
        bandgrafdat = Dgraph()

        # Set up frontier
        # C code: line 166 - only first vertex in frontier
        # C code: line 168 - only rank 1 has 1 frontier vertex, others have 0
        fronloctab[0] = baseval
        fronlocnbr = 1 if rank == 1 else 0

        # Compute band graph
        # C code: line 93
        # Parameters:
        #   fronlocnbr - number of frontier vertices on this rank
        #   fronloctab - array of frontier vertex indices
        #   distmax=4 - maximum distance from frontier (bandwidth)
        #   bandgrafdat - output band graph
        if grafdat.band(fronlocnbr, fronloctab, 4, bandgrafdat) != 0:
            print(f"ERROR: cannot compute band graph")
            grafdat.exit()
            mpi.finalize()
            os._exit(1)

        # Get band graph data (need vertex counts and labels)
        # C code: line 175
        band_data = bandgrafdat.data(
            want_baseval=True,
            want_vertglbnbr=True,
            want_vertlocnbr=True,
            want_vlblloctab=True  # Vertex labels!
        )
        band_baseval = band_data['baseval']
        bandvertglbnbr = band_data['vertglbnbr']
        bandvertlocnbr = band_data['vertlocnbr']
        bandvlblloctab = band_data['vlblloctab']

        # Write mapping to file (sequential output with barriers)
        # C code: lines 177-196
        for procnum in range(size):
            mpi.barrier()

            if procnum == rank:
                # Open file (first rank writes, others append)
                mode = 'w' if procnum == 0 else 'a'

                with open(mapping_file, mode) as f:
                    if procnum == 0:
                        # First rank writes header
                        f.write(f"{bandvertglbnbr}\n")

                    # Write vertex labels with partition value 1
                    # C code: lines 191-192
                    for bandvertlocnum in range(bandvertlocnbr):
                        # TODO: Need to dereference pointer from vlblloctab
                        # C code: bandvlblloctab[bandvertlocnum]
                        # Our data() returns a pointer, need to access it properly
                        label = bandvlblloctab[bandvertlocnum]
                        f.write(f"{label}\t1\n")

        # Clean up
        bandgrafdat.exit()
        grafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Band test completed successfully")
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
