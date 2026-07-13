"""Quick tour of the main PyScotch API."""
import numpy as np
from pyscotch import (
    Graph, Mesh, Architecture, Strategy, Strategies,
    Mapping, Ordering, scotch_version, random_reset,
)

# Check Scotch version
major, minor, patch = scotch_version()
print(f"Scotch version: {major}.{minor}.{patch}")
assert major >= 7, "Requires Scotch 7+"

# Build a graph from an edge list (convenience method)
edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
with Graph.from_edges(edges, num_vertices=4) as g:
    assert g.check()
    v, e = g.size()
    print(f"Graph: {v} vertices, {e} edge entries")

    # Partition
    random_reset()
    parts = g.partition(nparts=2)
    print(f"Partition: {parts}")

    # Color
    random_reset()
    colors, num_colors = g.color()
    print(f"Coloring: {colors} ({num_colors} colors)")

    # Verify coloring: no two adjacent vertices share a color
    for u, w in edges:
        assert colors[u] != colors[w], f"Adjacent vertices {u},{w} share color"

# Architecture
with Architecture() as arch:
    arch.complete(4)
    assert arch.size() == 4
    assert arch.name() == "cmplt"
    print(f"Architecture: {arch.name()}, {arch.size()} domains")
