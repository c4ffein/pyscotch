#!/usr/bin/env python3
"""
Mesh Partitioning Example

This example demonstrates how to:
1. Load a mesh from a file
2. Partition the mesh
3. Convert mesh to graph
4. Analyze the partition

Usage:
    python mesh_partitioning.py <mesh_file> <num_parts>

Example:
    python mesh_partitioning.py ../external/scotch/src/check/data/m4x4.msh 4
"""

import sys
from pathlib import Path

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscotch import Mesh, Graph, Architecture, Strategies


def partition_mesh(mesh_file: Path, num_parts: int):
    """Partition a mesh and analyze results."""

    print(f"Loading mesh from: {mesh_file}")

    # Create mesh and load from file
    mesh = Mesh()
    mesh.load(mesh_file)
    print("✓ Mesh loaded")

    # Validate mesh structure
    if not mesh.check():
        print("ERROR: Mesh validation failed!")
        return 1
    print("✓ Mesh structure validated")

    # Create target architecture (complete graph with k vertices)
    arch = Architecture.complete_graph(num_parts)
    print(f"Target architecture: {num_parts} parts")

    # Create partitioning strategy
    strategy = Strategies.partition_quality()
    print("Using quality partitioning strategy")

    # Perform mesh partitioning
    print(f"\nPartitioning mesh into {num_parts} parts...")
    mapping = mesh.partition(arch, strategy)
    print("✓ Mesh partitioned")

    # Get partition array
    parttab = mapping.get_partition_array()

    # Analyze partition quality
    print("\n=== Partition Analysis ===")

    # Count elements in each partition
    import numpy as np
    part_sizes = np.bincount(parttab, minlength=num_parts)
    print(f"Partition sizes: {part_sizes}")

    # Calculate balance
    avg_size = len(parttab) / num_parts
    max_size = part_sizes.max()
    imbalance = (max_size - avg_size) / avg_size * 100
    print(f"Average partition size: {avg_size:.1f}")
    print(f"Maximum partition size: {max_size}")
    print(f"Imbalance: {imbalance:.2f}%")

    # Convert mesh to graph for additional analysis
    print("\n=== Converting Mesh to Graph ===")
    graph = Graph()
    mesh.to_graph(graph)
    print("✓ Mesh converted to graph")

    # Validate graph
    if not graph.check():
        print("ERROR: Converted graph validation failed!")
        mesh.exit()
        graph.exit()
        return 1
    print("✓ Graph structure validated")

    # Get graph statistics
    vertnbr, edgenbr = graph.size()
    print(f"Graph: {vertnbr} vertices, {edgenbr} edges")

    # Cleanup
    graph.exit()
    mesh.exit()

    print("\n✓ Mesh partitioning complete!")
    return 0


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <mesh_file> <num_parts>")
        print(f"\nExample:")
        print(f"  {sys.argv[0]} ../external/scotch/src/check/data/m4x4.msh 4")
        return 1

    mesh_file = Path(sys.argv[1])
    if not mesh_file.exists():
        print(f"ERROR: Mesh file not found: {mesh_file}")
        return 1

    try:
        num_parts = int(sys.argv[2])
        if num_parts < 2:
            print("ERROR: num_parts must be >= 2")
            return 1
    except ValueError:
        print("ERROR: num_parts must be an integer")
        return 1

    return partition_mesh(mesh_file, num_parts)


if __name__ == "__main__":
    sys.exit(main())
