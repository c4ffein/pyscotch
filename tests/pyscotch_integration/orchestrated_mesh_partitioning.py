#!/usr/bin/env python3
"""
Orchestrated Integration Test: Mesh Partitioning Workflow

Runs as a standalone script for subprocess isolation.
"""
import sys
from pathlib import Path
import numpy as np

from pyscotch import Mesh


def main():
    """Run mesh partitioning workflow tests."""
    try:
        mesh_file = Path("external/scotch/src/check/data/cube_8.msh")

        if not mesh_file.exists():
            print(f"ERROR: Mesh file not found: {mesh_file}")
            return 1

        print("=== Mesh Partitioning Workflow ===\n")

        # Test 1: Complete mesh workflow
        print("[Test 1] Load → Partition → Convert → Validate")
        mesh = Mesh()
        mesh.load(mesh_file)

        num_parts = 4
        parttab = mesh.partition(num_parts)

        assert len(parttab) > 0, "Empty partition"
        assert np.all(parttab >= 0) and np.all(parttab < num_parts), "Invalid partition IDs"

        # Convert to graph
        graph = mesh.to_graph()
        assert graph.check(), "Graph validation failed after conversion"
        vertnbr, edgenbr = graph.size()
        print(f"  Converted to graph: {vertnbr} vertices, {edgenbr} edges")

        # Check balance
        part_sizes = np.bincount(parttab, minlength=num_parts)
        assert np.all(part_sizes > 0), "Empty partitions"

        avg_size = len(parttab) / num_parts
        imbalance = part_sizes.max() / avg_size
        assert imbalance < 2.0, f"Too imbalanced: {imbalance:.2f}"

        print(f"  ✓ Partitioned into {num_parts} parts, imbalance: {imbalance:.2f}")

        # Test 2: Multiple partition sizes
        print("\n[Test 2] Multiple partition sizes")
        for nparts in [2, 4, 8]:
            mesh = Mesh()
            mesh.load(mesh_file)
            parttab = mesh.partition(nparts)

            assert len(parttab) > 0, f"Empty partition for {nparts} parts"
            assert np.all(parttab >= 0) and np.all(parttab < nparts), "Invalid partition IDs"
            print(f"  ✓ {nparts} parts OK")

        # Test 3: Mesh check
        print("\n[Test 3] Mesh validation")
        mesh = Mesh()
        mesh.load(mesh_file)
        assert mesh.check(), "Mesh validation failed"
        print("  ✓ Mesh check OK")

        print("\n=== All Mesh Partitioning Tests PASSED ===\n")
        return 0

    except AssertionError as e:
        print(f"ASSERTION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
