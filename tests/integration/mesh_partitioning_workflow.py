#!/usr/bin/env python3
"""
Integration Test: Mesh Partitioning Workflow

This validates a complete end-to-end mesh workflow:
1. Load mesh from file
2. Partition mesh
3. Convert to graph
4. Validate connectivity and structure

Run with: python mesh_partitioning_workflow.py
"""
import sys
from pathlib import Path
import numpy as np

# Add pyscotch to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyscotch import Mesh, Graph, Architecture, Strategies


def main():
    """Test mesh partitioning workflow."""
    try:
        mesh_file = Path("external/scotch/src/check/data/cube_8.msh")

        if not mesh_file.exists():
            print(f"ERROR: Mesh file not found: {mesh_file}")
            return 1

        print("=== Mesh Partitioning Workflow Integration Test ===\n")

        # Test 1: Complete mesh workflow
        print("[Test 1] Complete mesh workflow (load → partition → convert → validate)")

        mesh = Mesh()
        mesh.load(mesh_file)

        # Partition mesh
        num_parts = 4
        arch = Architecture.complete_graph(num_parts)

        mapping = mesh.partition(arch)
        parttab = mapping.get_partition_array()

        if len(parttab) == 0:
            print("ERROR: Partition array is empty")
            return 1

        # Validate partition
        part_sizes = np.bincount(parttab, minlength=num_parts)

        if not np.all(part_sizes > 0):
            print("ERROR: Not all partitions used")
            return 1

        # Check partition IDs are valid
        if not np.all(parttab >= 0) or not np.all(parttab < num_parts):
            print("ERROR: Invalid partition IDs")
            return 1

        print(f"  Partitioned into {num_parts} parts")
        print(f"  Partition sizes: {part_sizes}")

        # Convert mesh to graph
        graph = Graph()
        mesh.to_graph(graph)

        # Validate converted graph
        if not graph.check():
            print("ERROR: Converted graph is not valid")
            return 1

        # Get graph statistics
        vertnbr, edgenbr = graph.size()

        if vertnbr == 0 or edgenbr == 0:
            print("ERROR: Converted graph has no vertices or edges")
            return 1

        # Mesh conversion should preserve connectivity
        edge_per_vertex = edgenbr / vertnbr

        if edge_per_vertex <= 0 or edge_per_vertex >= 100:
            print(f"ERROR: Edge/vertex ratio unreasonable: {edge_per_vertex}")
            return 1

        print(f"  Converted to graph: {vertnbr} vertices, {edgenbr} edges")
        print(f"  Edge/vertex ratio: {edge_per_vertex:.2f}")
        print("  ✓ Complete mesh workflow PASSED")


        # Test 2: Different partition sizes
        print("\n[Test 2] Mesh partitioning with different partition counts")

        mesh = Mesh()
        mesh.load(mesh_file)

        for num_parts in [2, 3, 4]:
            arch = Architecture.complete_graph(num_parts)
            mapping = mesh.partition(arch)
            parttab = mapping.get_partition_array()

            part_sizes = np.bincount(parttab, minlength=num_parts)

            if not np.all(part_sizes > 0):
                print(f"ERROR: Not all {num_parts} partitions used")
                return 1

            # Check balance
            avg_size = len(parttab) / num_parts
            max_size = part_sizes.max()
            imbalance_ratio = max_size / avg_size

            if imbalance_ratio >= 2.5:
                print(f"ERROR: Partition too imbalanced (ratio={imbalance_ratio})")
                return 1

        print(f"  Tested partition sizes: 2, 3, 4")
        print("  ✓ Different partition sizes PASSED")

        # Test 3: Mesh to graph consistency
        print("\n[Test 3] Mesh→graph conversion consistency")

        mesh = Mesh()
        mesh.load(mesh_file)

        # Convert to graph twice
        graph1 = Graph()
        mesh.to_graph(graph1)

        graph2 = Graph()
        mesh.to_graph(graph2)

        # Both graphs should be valid
        if not graph1.check() or not graph2.check():
            print("ERROR: Converted graphs not valid")
            graph1.exit()
            graph2.exit()
            return 1

        # Both should have same size
        v1, e1 = graph1.size()
        v2, e2 = graph2.size()

        if v1 != v2 or e1 != e2:
            print(f"ERROR: Converted graphs differ: ({v1},{e1}) != ({v2},{e2})")
            graph1.exit()
            graph2.exit()
            return 1

        print(f"  Both conversions: {v1} vertices, {e1} edges")
        print("  ✓ Mesh→graph consistency PASSED")

        graph1.exit()
        graph2.exit()

        # Test 4: Partition preserves structure
        print("\n[Test 4] Partitioning preserves mesh structure")

        mesh = Mesh()
        mesh.load(mesh_file)

        # Partition
        num_parts = 4
        mapping = mesh.partition(num_parts)
        parttab = mapping.get_partition_array()

        # Convert to graph
        graph = Graph()
        mesh.to_graph(graph)

        # Graph should be valid
        if not graph.check():
            print("ERROR: Graph from partitioned mesh invalid")
            return 1

        print("  Mesh remains valid after partitioning")
        print("  Converted graph is valid")
        print("  ✓ Structure preservation PASSED")


        # Test 5: Repeat partitioning
        print("\n[Test 5] Repeat mesh partitioning for consistency")

        mesh = Mesh()
        mesh.load(mesh_file)

        num_parts = 4
        arch = Architecture.complete_graph(num_parts)

        # Partition twice
        mapping1 = mesh.partition(arch)
        parttab1 = mapping1.get_partition_array()

        mapping2 = mesh.partition(arch)
        parttab2 = mapping2.get_partition_array()

        # Both should produce valid partitions
        for i, parttab in enumerate([parttab1, parttab2], 1):
            part_sizes = np.bincount(parttab, minlength=num_parts)

            if not np.all(part_sizes > 0):
                print(f"ERROR: Partition {i} didn't use all partitions")
                return 1

            if len(parttab) == 0:
                print(f"ERROR: Partition {i} is empty")
                return 1

        # Both should partition same number of elements
        if len(parttab1) != len(parttab2):
            print("ERROR: Different partitions have different sizes")
            return 1

        print(f"  Both partitioned {len(parttab1)} elements")
        print("  ✓ Repeat partitioning PASSED")


        # Test 6: Mesh and graph partitions
        print("\n[Test 6] Partitioning mesh and converted graph")

        mesh = Mesh()
        mesh.load(mesh_file)

        num_parts = 4

        # Partition mesh
        mesh_mapping = mesh.partition(num_parts)
        mesh_parttab = mesh_mapping.get_partition_array()

        # Convert to graph
        graph = Graph()
        mesh.to_graph(graph)

        # Partition graph
        graph_parttab = graph.partition(num_parts)

        # Both partitions should be valid
        mesh_part_sizes = np.bincount(mesh_parttab, minlength=num_parts)
        graph_part_sizes = np.bincount(graph_parttab, minlength=num_parts)

        if not np.all(mesh_part_sizes > 0) or not np.all(graph_part_sizes > 0):
            print("ERROR: Not all partitions used in mesh or graph")
            return 1

        # Check balance
        mesh_balance = mesh_part_sizes.max() / mesh_part_sizes.mean()
        graph_balance = graph_part_sizes.max() / graph_part_sizes.mean()

        if mesh_balance >= 2.0 or graph_balance >= 2.0:
            print("ERROR: Partition imbalance too high")
            return 1

        print(f"  Mesh partition balance: {mesh_balance:.2f}")
        print(f"  Graph partition balance: {graph_balance:.2f}")
        print("  ✓ Mesh and graph partitions PASSED")


        # Test 7: Larger mesh if available
        print("\n[Test 7] Larger mesh (if available)")

        large_mesh = Path("external/scotch/src/check/data/ship001.msh")

        if not large_mesh.exists():
            print("  Large mesh file not found, skipping")
        else:
            mesh = Mesh()
            mesh.load(large_mesh)

            # Partition into more parts
            num_parts = 8
            mapping = mesh.partition(num_parts)
            parttab = mapping.get_partition_array()

            part_sizes = np.bincount(parttab, minlength=num_parts)

            if not np.all(part_sizes > 0):
                print("ERROR: Not all partitions used for large mesh")
                return 1

            # Convert and validate
            graph = Graph()
            mesh.to_graph(graph)

            if not graph.check():
                print("ERROR: Graph from large mesh invalid")
                return 1

            v, e = graph.size()
            print(f"  Large mesh: {len(parttab)} elements")
            print(f"  Converted graph: {v} vertices, {e} edges")
            print("  ✓ Large mesh PASSED")


        print("\n=== All Mesh Partitioning Workflow Tests PASSED ===\n")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
