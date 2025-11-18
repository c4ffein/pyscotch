#!/usr/bin/env python3
"""
Port of test_scotch_dgraph_induce.c

Tests the SCOTCH_dgraphInducePart() routine.
Extracts an induced subgraph for vertices belonging to a specific partition.

Reference: external/scotch/src/check/test_scotch_dgraph_induce.c

Run with: mpirun -np 3 python dgraph_induce_part.py <graph_file>
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
    """Test dgraph induced subgraph extraction."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        # Check arguments
        # C code: lines 102-105
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

        # Set active variant (64-bit parallel)
        lib.set_active_variant(64, parallel=True)

        # Barrier: Synchronize for debug
        # C code: line 122
        mpi.barrier()

        # Initialize source graph
        # C code: lines 127-130
        orggrafdat = Dgraph()

        # Load source graph
        # C code: lines 139-142
        orggrafdat.load(graph_file, baseval=-1, flagval=0)

        # Barrier: Synchronize after load
        # C code: line 147
        mpi.barrier()

        # Get graph data (need baseval and vertex count)
        # C code: line 152
        data = orggrafdat.data(
            want_baseval=True,
            want_vertlocnbr=True
        )
        baseval = data['baseval']
        orgvertlocnbr = data['vertlocnbr']

        # Allocate partition and index arrays
        # C code: lines 154-161
        orgpartloctab = np.zeros(orgvertlocnbr, dtype=lib.get_scotch_dtype())
        indlistloctab = np.zeros(orgvertlocnbr, dtype=lib.get_scotch_dtype())  # TRICK: size is orgvertlocnbr

        # Initialize random generator and create shuffled index list
        # C code: lines 163-175
        import random
        random.seed(42)  # Use fixed seed for determinism (replaces SCOTCH_randomReset)

        # Fill index list with sequential vertex numbers
        # C code: lines 164-166
        for orgvertlocnum in range(orgvertlocnbr):
            indlistloctab[orgvertlocnum] = baseval + orgvertlocnum

        # Shuffle the index list (Fisher-Yates shuffle)
        # C code: lines 167-175
        for orgvertlocnum in range(orgvertlocnbr):
            # Random value from [orgvertlocnum, orgvertlocnbr)
            orgvertloctmp = orgvertlocnum + random.randint(0, orgvertlocnbr - orgvertlocnum - 1)

            # Swap
            indlistloctmp = indlistloctab[orgvertlocnum]
            indlistloctab[orgvertlocnum] = indlistloctab[orgvertloctmp]
            indlistloctab[orgvertloctmp] = indlistloctmp

        # Keep only half of the original vertices
        # C code: line 177
        indvertlocnbr = (orgvertlocnbr + 1) // 2

        # Initialize partition array to 0 (part 0)
        # C code: line 179
        # (already initialized to 0 by np.zeros above)

        # Flag kept vertices as belonging to part 1
        # C code: lines 180-181
        for indvertlocnum in range(indvertlocnbr):
            orgpartloctab[indlistloctab[indvertlocnum] - baseval] = 1

        # Initialize induced graph
        # C code: lines 183-186
        indgrafdat = Dgraph()

        # Extract induced subgraph for partition 1
        # C code: line 187
        # Parameters:
        #   orggrafdat - original distributed graph
        #   orgpartloctab - partition array (which partition each vertex belongs to)
        #   partval=1 - which partition to extract (partition 1)
        #   indvertlocnbr - number of vertices in partition 1 on local rank
        #   indgrafdat - output induced subgraph
        if orggrafdat.induce_part(orgpartloctab, 1, indvertlocnbr, indgrafdat) != 0:
            print(f"ERROR: cannot induce graph")
            orggrafdat.exit()
            indgrafdat.exit()
            mpi.finalize()
            os._exit(1)

        # Check induced graph
        # C code: lines 191-193
        if not indgrafdat.check():
            print(f"ERROR: invalid induced graph")
            orggrafdat.exit()
            indgrafdat.exit()
            mpi.finalize()
            os._exit(1)

        # Clean up
        # C code: lines 196-197
        indgrafdat.exit()
        orggrafdat.exit()

        # MPI finalize
        # C code: line 202
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Induce test completed successfully")
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
