"""Demonstrate context manager usage for safe resource cleanup."""
import numpy as np
from pyscotch import Graph, Strategy

# All Scotch objects support `with` for automatic cleanup
with Graph() as graph:
    verttab = np.array([0, 2, 4, 6], dtype=np.int64)
    edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=np.int64)
    graph.build(verttab, edgetab)

    with Strategy() as strategy:  # a fresh Strategy is Scotch's default
        partitions = graph.partition(nparts=2, strategy=strategy)
        assert len(partitions) == 3
    # strategy.close() called automatically here

# graph.close() called automatically here
print("Resources cleaned up safely")
