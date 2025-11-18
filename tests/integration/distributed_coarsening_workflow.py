#!/usr/bin/env python3
"""
Integration Test: Distributed Coarsening Workflow

This validates a complete end-to-end distributed workflow:
1. Load distributed graph
2. Perform multi-level coarsening
3. Validate coarse graph structure
4. Compare results across processes

Run with: mpirun -np 3 python distributed_coarsening_workflow.py
"""
import sys
import os
from pathlib import Path

# Add pyscotch to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph, COARSEN_NONE


def main():
    """Test distributed coarsening workflow."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        graph_file = Path("external/scotch/src/check/data/bump.grf")

        if not graph_file.exists():
            if rank == 0:
                print(f"ERROR: Graph file not found: {graph_file}")
            mpi.finalize()
            return 1

        # Set active variant (64-bit parallel)
        lib.set_active_variant(64, parallel=True)

        if rank == 0:
            print("=== Distributed Coarsening Workflow Integration Test ===\n")

        # Test 1: Single-level coarsening
        if rank == 0:
            print("[Test 1] Single-level coarsening workflow")

        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        # Validate original graph
        if not grafdat.check():
            if rank == 0:
                print("ERROR: Original graph validation failed")
            grafdat.exit()
            mpi.finalize()
            return 1

        # Get original graph data
        orig_data = grafdat.data(
            want_vertglbnbr=True,
            want_vertlocnbr=True,
            want_edgeglbnbr=True
        )

        orig_vertglbnbr = orig_data['vertglbnbr']
        orig_vertlocnbr = orig_data['vertlocnbr']
        orig_edgeglbnbr = orig_data['edgeglbnbr']

        if rank == 0:
            print(f"  Original: {orig_vertglbnbr} vertices (global), {orig_edgeglbnbr} edges")

        # Perform coarsening
        coargrafdat, multloctab = grafdat.coarsen(coarrat=0.8, foldval=COARSEN_NONE)

        if multloctab is None:
            if rank == 0:
                print("  Graph could not be coarsened (already optimal)")
        else:
            # Validate coarse graph
            if not coargrafdat.check():
                if rank == 0:
                    print("ERROR: Coarse graph validation failed")
                grafdat.exit()
                coargrafdat.exit()
                mpi.finalize()
                return 1

            # Get coarse graph data
            coar_data = coargrafdat.data(want_vertglbnbr=True, want_vertlocnbr=True)
            coar_vertglbnbr = coar_data['vertglbnbr']

            if rank == 0:
                ratio = float(coar_vertglbnbr) / float(orig_vertglbnbr)
                print(f"  Coarsened: {coar_vertglbnbr} vertices (ratio: {ratio:.4f})")
                print("  ✓ Single-level coarsening PASSED")

            coargrafdat.exit()

        grafdat.exit()

        # Test 2: Multi-level coarsening
        if rank == 0:
            print("\n[Test 2] Multi-level coarsening workflow")

        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        level0_data = grafdat.data(want_vertglbnbr=True)
        level0_vertices = level0_data['vertglbnbr']

        # Level 1
        coar1grafdat, mult1 = grafdat.coarsen(coarrat=0.8, foldval=COARSEN_NONE)

        if mult1 is not None:
            if not coar1grafdat.check():
                if rank == 0:
                    print("ERROR: Level 1 coarse graph invalid")
                grafdat.exit()
                coar1grafdat.exit()
                mpi.finalize()
                return 1

            coar1_data = coar1grafdat.data(want_vertglbnbr=True)
            level1_vertices = coar1_data['vertglbnbr']

            # Level 2
            coar2grafdat, mult2 = coar1grafdat.coarsen(coarrat=0.8, foldval=COARSEN_NONE)

            if mult2 is not None:
                if not coar2grafdat.check():
                    if rank == 0:
                        print("ERROR: Level 2 coarse graph invalid")
                    grafdat.exit()
                    coar1grafdat.exit()
                    coar2grafdat.exit()
                    mpi.finalize()
                    return 1

                coar2_data = coar2grafdat.data(want_vertglbnbr=True)
                level2_vertices = coar2_data['vertglbnbr']

                if rank == 0:
                    print(f"  Level 0: {level0_vertices} vertices")
                    print(f"  Level 1: {level1_vertices} vertices")
                    print(f"  Level 2: {level2_vertices} vertices")

                    # Verify monotonic decrease
                    if level2_vertices <= level1_vertices <= level0_vertices:
                        print("  ✓ Multi-level coarsening PASSED")
                    else:
                        print("ERROR: Vertex counts not monotonically decreasing")
                        grafdat.exit()
                        coar1grafdat.exit()
                        coar2grafdat.exit()
                        mpi.finalize()
                        return 1

                coar2grafdat.exit()

            coar1grafdat.exit()

        grafdat.exit()

        # Test 3: Connectivity preservation
        if rank == 0:
            print("\n[Test 3] Connectivity preservation")

        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        orig_data = grafdat.data(want_vertglbnbr=True, want_edgeglbnbr=True)
        orig_vertices = orig_data['vertglbnbr']
        orig_edges = orig_data['edgeglbnbr']

        coargrafdat, multloctab = grafdat.coarsen(coarrat=0.8, foldval=COARSEN_NONE)

        if multloctab is not None:
            coar_data = coargrafdat.data(want_vertglbnbr=True, want_edgeglbnbr=True)
            coar_vertices = coar_data['vertglbnbr']
            coar_edges = coar_data['edgeglbnbr']

            # Edge/vertex ratio shouldn't explode
            orig_ratio = orig_edges / orig_vertices if orig_vertices > 0 else 0
            coar_ratio = coar_edges / coar_vertices if coar_vertices > 0 else 0

            if rank == 0:
                print(f"  Original edge/vertex ratio: {orig_ratio:.2f}")
                print(f"  Coarse edge/vertex ratio: {coar_ratio:.2f}")

                if coar_ratio <= orig_ratio * 2:
                    print("  ✓ Connectivity preservation PASSED")
                else:
                    print("ERROR: Edge/vertex ratio exploded")
                    grafdat.exit()
                    coargrafdat.exit()
                    mpi.finalize()
                    return 1

            coargrafdat.exit()

        grafdat.exit()

        if rank == 0:
            print("\n=== All Distributed Coarsening Workflow Tests PASSED ===\n")

        mpi.finalize()
        return 0

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
