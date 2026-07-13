"""Basic graph partitioning into k parts."""
import numpy as np
from pyscotch import Graph, Mapping, random_reset

# 3x3 grid graph (9 vertices)
edges = []
for r in range(3):
    for c in range(3):
        v = r * 3 + c
        if c < 2:
            edges.append((v, v + 1))
        if r < 2:
            edges.append((v, v + 3))

with Graph.from_edges(edges, num_vertices=9) as graph:
    random_reset()
    parts = graph.partition(nparts=3)

    mapping = Mapping(parts)
    print(f"Parts: {parts}")
    print(f"Sizes: {mapping.get_partition_sizes()}")
    print(f"Balance: {mapping.balance():.2f}")

    # Each partition should have 3 vertices (perfect balance for 9/3)
    assert mapping.num_partitions() == 3
    assert all(s == 3 for s in mapping.get_partition_sizes()), \
        f"Expected perfect balance, got {mapping.get_partition_sizes()}"
