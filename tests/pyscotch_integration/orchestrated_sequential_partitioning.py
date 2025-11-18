#!/usr/bin/env python3
"""
Orchestrated Integration Test: Sequential Partitioning Workflow

Runs as a standalone script for subprocess isolation.
"""
import sys
from pathlib import Path
import numpy as np

from pyscotch import Graph


def main():
    """Run sequential partitioning workflow tests."""
    try:
        graph_file = Path("external/scotch/src/check/data/bump.grf")

        if not graph_file.exists():
            print(f"ERROR: Graph file not found: {graph_file}")
            return 1

        print("=== Sequential Partitioning Workflow ===\n")

        # Test 1: Complete workflow
        print("[Test 1] Load → Partition → Validate")
        graph = Graph()
        graph.load(graph_file)

        assert graph.check(), "Graph validation failed"
        vertnbr, edgenbr = graph.size()
        print(f"  Loaded: {vertnbr} vertices, {edgenbr} edges")

        num_parts = 4
        parttab = graph.partition(num_parts)

        assert len(parttab) == vertnbr, "Partition size mismatch"
        part_sizes = np.bincount(parttab, minlength=num_parts)
        assert np.all(part_sizes > 0), "Empty partitions found"

        avg_size = vertnbr / num_parts
        imbalance = part_sizes.max() / avg_size
        assert imbalance < 2.0, f"Too imbalanced: {imbalance:.2f}"

        print(f"  ✓ Partitioned into {num_parts} parts, imbalance: {imbalance:.2f}")

        # Test 2: Multiple partition sizes
        print("\n[Test 2] Multiple partition sizes")
        for nparts in [2, 4, 8]:
            graph = Graph()
            graph.load(graph_file)
            parttab = graph.partition(nparts)

            assert len(parttab) == vertnbr, f"Size mismatch for {nparts} parts"
            assert np.all(parttab >= 0) and np.all(parttab < nparts), "Invalid partition IDs"
            print(f"  ✓ {nparts} parts OK")

        print("\n=== All Sequential Partitioning Tests PASSED ===\n")
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
