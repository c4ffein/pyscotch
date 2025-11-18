#!/usr/bin/env python3
"""
Distributed Graph Coarsening Example

This example demonstrates how to:
1. Load a distributed graph with MPI
2. Perform multi-level coarsening
3. Validate the coarse graph
4. Compare results across processes

Usage:
    mpirun -np <num_procs> python distributed_coarsening.py <graph_file>

Example:
    mpirun -np 3 python distributed_coarsening.py ../external/scotch/src/check/data/bump.grf
"""

import sys
import os
from pathlib import Path

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph, COARSEN_NONE, COARSEN_FOLD


def distributed_coarsening_example(graph_file: Path):
    """Demonstrate distributed graph coarsening."""

    # Initialize MPI
    mpi.init()
    rank = mpi.comm_rank()
    size = mpi.comm_size()

    try:
        # Set active variant (64-bit parallel)
        lib.set_active_variant(64, parallel=True)

        if rank == 0:
            print(f"=== Distributed Graph Coarsening Example ===")
            print(f"Processes: {size}")
            print(f"Graph file: {graph_file}")
            print()

        # Load distributed graph
        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        if rank == 0:
            print("[1] Graph loaded successfully")

        # Synchronize
        mpi.barrier()

        # Get original graph data
        orig_data = grafdat.data(
            want_baseval=True,
            want_vertglbnbr=True,
            want_vertlocnbr=True,
            want_edgeglbnbr=True,
            want_edgelocnbr=True
        )

        baseval = orig_data['baseval']
        orig_vertglbnbr = orig_data['vertglbnbr']
        orig_vertlocnbr = orig_data['vertlocnbr']
        orig_edgeglbnbr = orig_data['edgeglbnbr']
        orig_edgelocnbr = orig_data['edgelocnbr']

        # Print original graph stats (rank 0 only)
        if rank == 0:
            print(f"\n[2] Original Graph Statistics:")
            print(f"    Global vertices: {orig_vertglbnbr}")
            print(f"    Global edges: {orig_edgeglbnbr}")
            print()

        # Print per-rank stats
        print(f"    Rank {rank}: {orig_vertlocnbr} vertices, {orig_edgelocnbr} edges")
        mpi.barrier()

        if rank == 0:
            print(f"\n[3] Performing coarsening (ratio=0.8, COARSEN_NONE)...")

        # Perform coarsening
        coargrafdat, multloctab = grafdat.coarsen(
            coarrat=0.8,
            foldval=COARSEN_NONE,
            flags=0
        )

        if multloctab is None:
            if rank == 0:
                print("    Graph could not be coarsened (already optimal)")
            grafdat.exit()
            mpi.finalize()
            return 0

        # Validate coarse graph
        if not coargrafdat.check():
            print(f"ERROR on rank {rank}: Coarse graph validation failed")
            grafdat.exit()
            coargrafdat.exit()
            mpi.finalize()
            return 1

        if rank == 0:
            print("    ✓ Coarse graph validated")

        # Get coarse graph data
        coar_data = coargrafdat.data(
            want_vertglbnbr=True,
            want_vertlocnbr=True,
            want_edgeglbnbr=True
        )

        coar_vertglbnbr = coar_data['vertglbnbr']
        coar_vertlocnbr = coar_data['vertlocnbr']
        coar_edgeglbnbr = coar_data['edgeglbnbr']

        # Print coarse graph stats
        if rank == 0:
            print(f"\n[4] Coarse Graph Statistics:")
            print(f"    Global vertices: {coar_vertglbnbr}")
            print(f"    Global edges: {coar_edgeglbnbr}")
            ratio = float(coar_vertglbnbr) / float(orig_vertglbnbr)
            print(f"    Coarsening ratio: {ratio:.4f}")
            print()

        # Print per-rank coarse stats
        print(f"    Rank {rank}: {coar_vertlocnbr} coarse vertices")
        mpi.barrier()

        # Try additional coarsening level
        if rank == 0:
            print(f"\n[5] Attempting second coarsening level...")

        coar2grafdat, multloctab2 = coargrafdat.coarsen(
            coarrat=0.8,
            foldval=COARSEN_NONE,
            flags=0
        )

        if multloctab2 is None:
            if rank == 0:
                print("    Second level coarsening stopped (graph optimal)")
        else:
            if rank == 0:
                print("    ✓ Second level coarsening successful")

            # Get level 2 stats
            coar2_data = coar2grafdat.data(
                want_vertglbnbr=True,
                want_edgeglbnbr=True
            )

            if rank == 0:
                print(f"    Level 2 vertices: {coar2_data['vertglbnbr']}")
                print(f"    Level 2 edges: {coar2_data['edgeglbnbr']}")

            # Cleanup level 2
            coar2grafdat.exit()

        # Cleanup
        coargrafdat.exit()
        grafdat.exit()

        if rank == 0:
            print(f"\n✓ Distributed coarsening example completed successfully!\n")

        mpi.finalize()
        return 0

    except Exception as e:
        print(f"ERROR on rank {rank}: {e}")
        import traceback
        traceback.print_exc()
        if mpi.is_initialized():
            mpi.finalize()
        return 1


def main():
    if len(sys.argv) != 2:
        if mpi.is_initialized() and mpi.comm_rank() == 0:
            print(f"Usage: mpirun -np <num_procs> {sys.argv[0]} <graph_file>")
            print(f"\nExample:")
            print(f"  mpirun -np 3 {sys.argv[0]} ../external/scotch/src/check/data/bump.grf")
        return 1

    graph_file = Path(sys.argv[1])
    if not graph_file.exists():
        if not mpi.is_initialized() or mpi.comm_rank() == 0:
            print(f"ERROR: Graph file not found: {graph_file}")
        return 1

    return distributed_coarsening_example(graph_file)


if __name__ == "__main__":
    sys.exit(main())
