"""Compute a fill-reducing ordering."""
import numpy as np
from pyscotch import Graph, Ordering, Strategies, random_reset

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
    strategy = Strategies.order_quality()
    permutation, inverse = graph.order(strategy)
    strategy.close()

    ordering = Ordering(permutation, inverse)
    print(f"Ordering size: {len(ordering)}")

    # Permutation should be a valid permutation of 0..15
    assert len(set(permutation)) == 16, "Permutation must have unique values"
    assert set(permutation) == set(range(16)), "Must be a permutation of 0..15"

    # Applying then inverting should give identity
    arr = np.arange(16)
    roundtrip = ordering.apply_inverse(ordering.apply(arr))
    assert np.array_equal(roundtrip, arr), "Roundtrip should be identity"
