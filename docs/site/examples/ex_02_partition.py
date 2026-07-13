"""Partition a graph into balanced parts."""
import numpy as np
from pyscotch import Graph, Mapping, Strategies, random_reset

# Build a 4x4 grid graph
edges = []
for r in range(4):
    for c in range(4):
        v = r * 4 + c
        if c < 3:
            edges.append((v, v + 1))
        if r < 3:
            edges.append((v, v + 4))

with Graph.from_edges(edges, num_vertices=16) as graph:
    random_reset()
    strategy = Strategies.partition_quality()
    partitions = graph.partition(nparts=4, strategy=strategy)
    strategy.close()

    mapping = Mapping(partitions)
    print(f"Partition sizes: {mapping.get_partition_sizes()}")
    print(f"Balance: {mapping.balance():.2f}")

    # Every vertex should be assigned to a valid partition
    assert np.all(partitions >= 0)
    assert np.all(partitions < 4)
    # All 4 partitions should be used
    assert mapping.num_partitions() == 4
