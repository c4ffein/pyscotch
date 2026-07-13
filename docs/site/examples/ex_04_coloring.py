"""Graph coloring: assign colors so no neighbors share one."""
import numpy as np
from pyscotch import Graph, random_reset

# Petersen graph (a classic graph theory example)
# 10 vertices, 15 edges
edges = [
    # Outer cycle
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 0),
    # Inner pentagram
    (5, 7), (7, 9), (9, 6), (6, 8), (8, 5),
    # Spokes
    (0, 5), (1, 6), (2, 7), (3, 8), (4, 9),
]

with Graph.from_edges(edges, num_vertices=10) as graph:
    random_reset()
    colors, num_colors = graph.color()

    print(f"Colors used: {num_colors}")
    print(f"Assignment: {colors}")

    # Verify: no adjacent vertices share a color
    for u, v in edges:
        assert colors[u] != colors[v], \
            f"Vertices {u} and {v} are adjacent but share color {colors[u]}"

    # Petersen graph has chromatic number 3
    # Scotch uses a greedy heuristic, so it might use more
    assert num_colors >= 3, "Need at least 3 colors for Petersen graph"
    print(f"Valid {num_colors}-coloring found!")
