"""Shared test fixtures for pyscotch_base tests."""

import pytest
from pyscotch import Graph


@pytest.fixture
def hexagon_graph():
    """A hexagon graph (6 vertices, degree 2 everywhere)."""
    return Graph.from_edges(
        [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)], num_vertices=6)


@pytest.fixture
def grid_4x4_graph():
    """A 4x4 grid graph (16 vertices)."""
    edges = []
    for r in range(4):
        for c in range(4):
            v = r * 4 + c
            if c < 3:
                edges.append((v, v + 1))
            if r < 3:
                edges.append((v, v + 4))
    return Graph.from_edges(edges, num_vertices=16)
