"""Demonstrate graph coarsening."""
import numpy as np
from pyscotch import Graph, random_reset

# Build a 4x4 grid graph (16 vertices)
edges = []
for r in range(4):
    for c in range(4):
        v = r * 4 + c
        if c < 3:
            edges.append((v, v + 1))
        if r < 3:
            edges.append((v, v + 4))

with Graph.from_edges(edges, num_vertices=16) as graph:
    vertnbr, _ = graph.size()
    assert vertnbr == 16

    random_reset()
    coarse_graph, multitab = graph.coarsen(coarrat=0.8)

    if coarse_graph is not None:
        coarse_verts, _ = coarse_graph.size()
        print(f"Original: {vertnbr} vertices -> Coarsened: {coarse_verts} vertices")
        assert coarse_verts < vertnbr, "Coarse graph should be smaller"
        coarse_graph.close()
    else:
        print("Graph too small to coarsen")
