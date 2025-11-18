#!/usr/bin/env python3
"""
Integration Test: Sequential Partitioning Workflow

This validates a complete end-to-end workflow:
1. Load graph from file
2. Partition with quality strategy
3. Validate partition balance and quality

Run with: python sequential_partitioning_workflow.py
"""
import sys
from pathlib import Path
import numpy as np

# Add pyscotch to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyscotch import Graph, Strategies
from pyscotch import libscotch as lib
from ctypes import byref, POINTER


def main():
    """Test sequential partitioning workflow."""
    try:
        graph_file = Path("external/scotch/src/check/data/bump.grf")

        if not graph_file.exists():
            print(f"ERROR: Graph file not found: {graph_file}")
            return 1

        print("=== Sequential Partitioning Workflow Integration Test ===\n")

        # Test 1: Complete partitioning workflow
        print("[Test 1] Complete partitioning workflow (load → partition → validate)")

        graph = Graph()
        graph.load(graph_file)

        # Validate loaded graph
        if not graph.check():
            print("ERROR: Graph validation failed after loading")
            return 1

        # Get graph size
        vertnbr, edgenbr = graph.size()
        print(f"  Loaded: {vertnbr} vertices, {edgenbr} edges")

        # Partition
        num_parts = 4
        parttab = graph.partition(num_parts)

        if len(parttab) != vertnbr:
            print(f"ERROR: Partition array size mismatch: {len(parttab)} != {vertnbr}")
            return 1

        # Validate partition
        part_sizes = np.bincount(parttab, minlength=num_parts)

        # Check all partitions are used
        if not np.all(part_sizes > 0):
            print(f"ERROR: Not all partitions used. Part sizes: {part_sizes}")
            print(f"  Unique partition IDs: {np.unique(parttab)}")
            return 1

        # Check balance
        avg_size = vertnbr / num_parts
        max_size = part_sizes.max()
        imbalance_ratio = max_size / avg_size

        print(f"  Partitioned into {num_parts} parts")
        print(f"  Partition sizes: {part_sizes}")
        print(f"  Imbalance ratio: {imbalance_ratio:.2f}")

        if imbalance_ratio >= 2.0:
            print("ERROR: Partition too imbalanced")
            return 1

        # Check partition IDs are valid
        if not np.all(parttab >= 0) or not np.all(parttab < num_parts):
            print("ERROR: Invalid partition IDs")
            return 1

        print("  ✓ Complete workflow PASSED")

        # Test 2: Multiple partition sizes
        print("\n[Test 2] Multiple partition sizes")

        graph = Graph()
        graph.load(graph_file)
        vertnbr, _ = graph.size()

        for num_parts in [2, 4, 8]:
            parttab = graph.partition(num_parts)

            if len(parttab) != vertnbr:
                print(f"ERROR: Size mismatch for {num_parts} parts")
                return 1

            part_sizes = np.bincount(parttab, minlength=num_parts)

            if not np.all(part_sizes > 0):
                print(f"ERROR: Not all {num_parts} partitions used")
                return 1

        print(f"  Tested partition sizes: 2, 4, 8")
        print("  ✓ Multiple partition sizes PASSED")

        # Test 3: Repeat partitioning
        print("\n[Test 3] Repeat partitioning for consistency")

        graph = Graph()
        graph.load(graph_file)
        vertnbr, _ = graph.size()
        num_parts = 4

        # Partition multiple times
        parttab1 = graph.partition(num_parts)
        parttab2 = graph.partition(num_parts)

        # Both should produce valid partitions
        for i, parttab in enumerate([parttab1, parttab2], 1):
            if len(parttab) != vertnbr:
                print(f"ERROR: Partition {i} size mismatch")
                return 1

            part_sizes = np.bincount(parttab, minlength=num_parts)
            if not np.all(part_sizes > 0):
                print(f"ERROR: Partition {i} didn't use all partitions")
                return 1

        print("  Both partitions use all parts")
        print("  ✓ Repeat partitioning PASSED")

        # Test 4: Partition from edges
        print("\n[Test 4] Partition graph created from edges")

        # Create a simple ring graph
        n = 20
        edges = [(i, (i + 1) % n) for i in range(n)]

        graph = Graph.from_edges(edges, num_vertices=n)

        if not graph.check():
            print("ERROR: Graph from edges not valid")
            return 1

        # Partition
        num_parts = 4
        parttab = graph.partition(num_parts)

        if len(parttab) != n:
            print(f"ERROR: Partition size mismatch: {len(parttab)} != {n}")
            return 1

        part_sizes = np.bincount(parttab, minlength=num_parts)

        if not np.all(part_sizes > 0):
            print("ERROR: Not all partitions used")
            return 1

        print(f"  Created ring graph with {n} vertices")
        print(f"  Partition sizes: {part_sizes}")
        print("  ✓ Partition from edges PASSED")

        # Test 5: Edge cut analysis
        print("\n[Test 5] Edge cut analysis")

        graph = Graph()
        graph.load(graph_file)

        # Partition
        num_parts = 4
        parttab = graph.partition(num_parts)

        # Get graph data to count edge cuts
        baseval = lib.SCOTCH_Num()
        vertnbr_c = lib.SCOTCH_Num()
        edgenbr_c = lib.SCOTCH_Num()
        verttab_ptr = POINTER(lib.SCOTCH_Num)()
        vendtab_ptr = POINTER(lib.SCOTCH_Num)()
        edgetab_ptr = POINTER(lib.SCOTCH_Num)()

        lib.SCOTCH_graphData(
            byref(graph._graph),
            byref(baseval),
            byref(vertnbr_c),
            byref(verttab_ptr),
            byref(vendtab_ptr),
            None,  # velotab
            None,  # vlbltab
            byref(edgenbr_c),
            byref(edgetab_ptr),
            None   # edlotab
        )

        vertnbr = vertnbr_c.value
        edgenbr = edgenbr_c.value

        # Count edge cuts
        edge_cuts = 0
        for v in range(vertnbr):
            v_part = parttab[v]
            edge_start = verttab_ptr[v] - baseval.value
            edge_end = vendtab_ptr[v] - baseval.value

            for e in range(edge_start, edge_end):
                neighbor = edgetab_ptr[e] - baseval.value
                if parttab[neighbor] != v_part:
                    edge_cuts += 1

        # Each edge cut is counted twice
        edge_cuts //= 2

        edge_cut_ratio = edge_cuts / edgenbr if edgenbr > 0 else 0

        print(f"  Edge cuts: {edge_cuts} / {edgenbr} ({edge_cut_ratio:.1%})")

        if edge_cuts >= edgenbr:
            print("ERROR: Edge cuts >= total edges")
            return 1

        if edge_cut_ratio >= 0.5:
            print("ERROR: Edge cut ratio too high")
            return 1

        print("  ✓ Edge cut analysis PASSED")

        print("\n=== All Sequential Partitioning Workflow Tests PASSED ===\n")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
