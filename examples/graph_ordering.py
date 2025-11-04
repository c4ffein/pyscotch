#!/usr/bin/env python3
"""
Example of graph ordering for sparse matrix factorization.

This example demonstrates how to compute an ordering of a graph,
which can be used to reduce fill-in during sparse matrix factorization.
"""

from pyscotch import Graph, Strategy, Ordering
import numpy as np

# Create a grid graph (5x5)
def create_grid_graph(n):
    """Create an n×n grid graph."""
    edges = []
    for i in range(n):
        for j in range(n):
            node = i * n + j
            # Connect to right neighbor
            if j < n - 1:
                edges.append((node, node + 1))
            # Connect to bottom neighbor
            if i < n - 1:
                edges.append((node, node + n))
    return edges

print("Creating 5x5 grid graph...")
edges = create_grid_graph(5)
graph = Graph.from_edges(edges, num_vertices=25)

vertnbr, edgenbr = graph.size()
print(f"Graph has {vertnbr} vertices and {edgenbr} edges")

# Compute ordering with default strategy
print("\nComputing ordering with default strategy...")
permutation, inverse = graph.order()

ordering = Ordering(permutation, inverse)
print(f"Ordering size: {len(ordering)}")

# Show first few elements of the permutation
print(f"First 10 elements of permutation: {permutation[:10]}")
print(f"First 10 elements of inverse: {inverse[:10]}")

# Apply ordering to a sample array
print("\nApplying ordering to array...")
original_array = np.arange(vertnbr)
reordered_array = ordering.apply(original_array)
print(f"Original: {original_array[:10]}")
print(f"Reordered: {reordered_array[:10]}")

# Verify inverse works correctly
restored_array = ordering.apply_inverse(reordered_array)
print(f"Restored: {restored_array[:10]}")
print(f"Matches original: {np.array_equal(original_array, restored_array)}")

# Try with nested dissection strategy
print("\nComputing ordering with nested dissection strategy...")
strategy = Strategy()
strategy.set_nested_dissection()
permutation, inverse = graph.order(strategy)

ordering = Ordering(permutation, inverse)
print(f"Nested dissection permutation: {permutation[:10]}")

print("\nDone!")
