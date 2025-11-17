#!/usr/bin/env python3
"""
Port of test_scotch_dgraph_coarsen.c

Tests the SCOTCH_dgraphCoarsen() routine with 3 coarsening modes:
- Plain coarsening (COARSEN_NONE)
- Folding (COARSEN_FOLD - reduces processes)
- Folding with duplication (COARSEN_FOLDDUP)

Reference: external/scotch/src/check/test_scotch_dgraph_coarsen.c

Run with: mpirun -np 3 python dgraph_coarsen.py <graph_file>
"""
import sys
from pathlib import Path

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph, COARSEN_NONE, COARSEN_FOLD, COARSEN_FOLDDUP


def main():
    """Test dgraph coarsening with multiple modes."""
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

        # Set active variant (64-bit parallel)
        lib.set_active_variant(64, parallel=True)

        # Load distributed graph
        finegrafdat = Dgraph()
        finegrafdat.load(graph_file, baseval=-1, flagval=0)

        # Barrier: Synchronize after load (for debug)
        mpi.barrier()

        # Get fine graph stats (only request vertex counts)
        fine_data = finegrafdat.data(want_vertglbnbr=True, want_vertlocnbr=True)
        finevertglbnbr = fine_data['vertglbnbr']
        finevertlocnbr = fine_data['vertlocnbr']

        # Coarsening ratio (0.8 = lazy coarsening)
        coarrat = 0.8

        # Test 3 different coarsening modes
        test_cases = [
            (COARSEN_NONE, "Plain coarsening"),
            (COARSEN_FOLD, "Folding"),
            (COARSEN_FOLDDUP, "Folding with duplication"),
        ]

        all_passed = True

        for foldval, foldstr in test_cases:
            if rank == 0:
                print(f"{foldstr}")

            # Get maximum multinode array size
            coarvertlocmax = finegrafdat.coarsen_vert_loc_max(foldval)

            # Perform coarsening
            coargrafdat, multloctab = finegrafdat.coarsen(
                coarrat=coarrat,
                foldval=foldval,
                flags=0
            )

            # Determine result status
            if multloctab is not None:
                # Graph was successfully coarsened
                # Now we can call data() on ALL ranks (including folded) by only requesting
                # safe scalar fields (vertex counts) and passing NULL for array pointers!
                # This matches Scotch's C test behavior.
                coar_data = coargrafdat.data(want_vertglbnbr=True, want_vertlocnbr=True)
                coarvertglbnbr = coar_data['vertglbnbr']
                coarvertlocnbr = coar_data['vertlocnbr']

                # Determine status message based on rank
                is_folded_rank = (foldval == COARSEN_FOLD) and (rank > (size // 2))
                if is_folded_rank:
                    coarstr = "folded graph not created here"
                else:
                    coarstr = "coarse graph created"

                # Print stats for each rank in sequence (matching Scotch's output loop)
                for procnum in range(size):
                    # Check multinode array size (exit immediately on error like Scotch)
                    if coarvertlocnbr > coarvertlocmax:
                        print(f"ERROR on rank {rank}: Invalid local multinode array size")
                        finegrafdat.exit()
                        coargrafdat.exit()
                        mpi.finalize()
                        import os
                        os._exit(1)

                    # Print when it's this rank's turn
                    if procnum == rank:
                        ratio = float(coarvertglbnbr) / float(finevertglbnbr) if finevertglbnbr > 0 else 0.0
                        print(f"{rank}: {coarstr} ({finevertlocnbr} / {coarvertlocmax} / {coarvertlocnbr} / {ratio:.6f})")

                    # Barrier: Ensures sequential output
                    mpi.barrier()

            else:
                # Graph could not be coarsened (not an error)
                coarstr = "graph could not be coarsened"
                print(f"{rank}: {coarstr}")

            # Clean up coarse graph
            try:
                coargrafdat.exit()
            except Exception as e:
                print(f"[Rank {rank}] Warning: error during coarse graph cleanup: {e}")

        # Clean up
        finegrafdat.exit()
        mpi.finalize()

        if all_passed:
            if rank == 0:
                print("\nPASS: All coarsening tests completed successfully")
            import os
            os._exit(0)
        else:
            if rank == 0:
                print("\nFAIL: Some coarsening tests failed")
            import os
            os._exit(1)

    except Exception as e:
        rank = mpi.comm_rank() if mpi.is_initialized() else '?'
        print(f"ERROR on rank {rank}: {e}")
        import traceback
        traceback.print_exc()
        if mpi.is_initialized():
            mpi.finalize()
        import os
        os._exit(1)


if __name__ == "__main__":
    main()
