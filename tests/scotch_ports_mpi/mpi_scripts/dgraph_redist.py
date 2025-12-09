#!/usr/bin/env python3
"""
Port of test_scotch_dgraph_redist.c

Tests the SCOTCH_dgraphRedist() routine.
Redistributes graph across processes according to a partition.

Reference: external/scotch/src/check/test_scotch_dgraph_redist.c

Run with: mpirun -np 3 python dgraph_redist.py <graph_file>
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
    """Test dgraph redistribution."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        # Check arguments
        if len(sys.argv) != 2:
            if rank == 0:
                print(f"usage: {sys.argv[0]} graph_file")
            mpi.finalize()
            return 1

        graph_file = Path(sys.argv[1])

        if not graph_file.exists():
            if rank == 0:
                print(f"ERROR: Graph file not found: {graph_file}")
            mpi.finalize()
            return 1

        # Note: PT-Scotch variant is set via environment variables:
        # PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1

        # Barrier: Synchronize for debug
        mpi.barrier()

        # Initialize source and destination graphs
        srcgrafdat = Dgraph()
        dstgrafdat = Dgraph()

        # Load source graph
        srcgrafdat.load(graph_file, baseval=-1, flagval=0)

        # Check source graph
        if not srcgrafdat.check():
            print(f"ERROR: invalid source graph")
            srcgrafdat.exit()
            mpi.finalize()
            os._exit(1)

        # Barrier: Synchronize after load
        mpi.barrier()

        # Get graph data (need vertex counts)
        data = srcgrafdat.data(
            want_vertglbnbr=True,
            want_vertlocnbr=True
        )
        vertglbnbr = data['vertglbnbr']
        vertlocnbr = data['vertlocnbr']

        # Allocate partition array
        # C code: lines 159-162
        partloctab = np.zeros(vertlocnbr, dtype=lib.get_scotch_dtype())

        # Create partitioning: packs of 3 vertices each, round-robin across processes
        # C code: lines 164-165
        for vertlocnum in range(vertlocnbr):
            partloctab[vertlocnum] = (vertlocnum // 3) % size

        # Redistribute graph according to partition
        # C code: line 95
        # Parameters:
        #   partloctab - target partition for each local vertex
        #   vsiztab=None - optional vertex sizes (None = uniform)
        #   procSrcTab=-1 - source process ID (-1 = use current)
        #   procDstTab=-1 - destination process ID (-1 = use partition from partloctab)
        #   dstgrafdat - output redistributed graph
        if srcgrafdat.redist(partloctab, None, -1, -1, dstgrafdat) != 0:
            print(f"ERROR: cannot compute redistributed graph")
            srcgrafdat.exit()
            dstgrafdat.exit()
            mpi.finalize()
            os._exit(1)

        # TODO: After redistribution, could verify destination graph
        # if not dstgrafdat.check():
        #     print(f"ERROR: invalid destination graph")
        #     ...

        # Clean up
        dstgrafdat.exit()
        srcgrafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Redist test completed successfully")
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
