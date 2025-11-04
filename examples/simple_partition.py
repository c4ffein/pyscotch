#!/usr/bin/env python3
"""
Simple example of graph partitioning with PyScotch.

This example demonstrates how to:
1. Create a graph from edge lists
2. Partition it into multiple parts
3. Analyze the partition quality
"""

from pyscotch import Graph, Strategy, Mapping

# Create a simple graph from edges
# This creates a small ring graph: 0-1-2-3-4-5-0
edges = [
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0),
    (0, 2), (1, 3), (2, 4), (3, 5), (4, 0), (5, 1),
]

print("Creating graph from edges...")
graph = Graph.from_edges(edges, num_vertices=6)

# Check graph validity
print(f"Graph is valid: {graph.check()}")

# Get graph size
vertnbr, edgenbr = graph.size()
print(f"Graph has {vertnbr} vertices and {edgenbr} edges")

# Partition into 2 parts using default strategy
print("\nPartitioning into 2 parts...")
nparts = 2
partitions = graph.partition(nparts)

# Analyze the partition
mapping = Mapping(partitions)
print(f"Partition balance: {mapping.balance():.3f}")
print(f"Partition sizes: {mapping.get_partition_sizes()}")

# Show which vertices are in each partition
for i in range(nparts):
    vertices = mapping.get_partition(i)
    print(f"Partition {i}: vertices {list(vertices)}")

# Try with quality strategy
print("\nPartitioning into 3 parts with quality strategy...")
from pyscotch import Strategies
strategy = Strategies.partition_quality()
partitions = graph.partition(3, strategy)

mapping = Mapping(partitions)
print(f"Partition balance: {mapping.balance():.3f}")
print(f"Partition sizes: {mapping.get_partition_sizes()}")

print("\nDone!")
