"""Compare partitioning strategies on different graph sizes."""
import numpy as np
from pyscotch import Graph, Strategies, Mapping, random_reset


def make_grid(n):
    """Build an n x n grid graph."""
    edges = []
    for r in range(n):
        for c in range(n):
            v = r * n + c
            if c < n - 1:
                edges.append((v, v + 1))
            if r < n - 1:
                edges.append((v, v + n))
    return Graph.from_edges(edges, num_vertices=n * n)


# Compare strategies on a medium-sized grid
with make_grid(10) as graph:
    vertnbr, _ = graph.size()

    # Quality preset: Scotch adaptive defaults, optimized for partition quality
    random_reset()
    with Strategies.partition_quality() as strat:
        parts_q = graph.partition(nparts=8, strategy=strat)

    # Fast preset: same defaults, balanced for speed
    random_reset()
    with Strategies.partition_fast() as strat:
        parts_f = graph.partition(nparts=8, strategy=strat)

    mq = Mapping(parts_q)
    mf = Mapping(parts_f)
    print(f"Graph: {vertnbr} vertices, 8 partitions")
    print(f"Quality: balance={mq.balance():.2f}, sizes={mq.get_partition_sizes()}")
    print(f"Fast:    balance={mf.balance():.2f}, sizes={mf.get_partition_sizes()}")

    # Both should produce valid 8-way partitions
    assert mq.num_partitions() == 8
    assert mf.num_partitions() == 8
    # Balance should be reasonable (within 2x of perfect)
    assert mq.balance() < 2.0, f"Quality balance too bad: {mq.balance()}"
    assert mf.balance() < 2.0, f"Fast balance too bad: {mf.balance()}"
