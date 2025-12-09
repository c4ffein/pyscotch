"""
Ported from: external/scotch/src/check/test_scotch_graph_color.c

Tests the SCOTCH_graphColor() routine for graph coloring.
The C test just verifies the function succeeds and prints a histogram.
"""

import pytest
import numpy as np
from pathlib import Path

from pyscotch import Graph
from pyscotch import libscotch as lib


class TestGraphColor:
    """Graph coloring tests from test_scotch_graph_color.c"""

    def test_color_triangle(self):
        """Color a simple triangle graph."""
        # Create triangle: 0-1-2-0
        edges = [(0, 1), (1, 2), (2, 0)]
        graph = Graph.from_edges(edges, num_vertices=3)

        colotab, colonbr = graph.color()

        # Verify function succeeded (only assertion from C test)
        assert colonbr > 0
        assert len(colotab) == 3

        # Print histogram like C test does
        color_counts = np.zeros(colonbr, dtype=np.int64)
        for color in colotab:
            color_counts[color] += 1

        print(f"\nTriangle graph: {colonbr} colors")
        for color_idx, count in enumerate(color_counts):
            print(f"  Color {color_idx}: {count} vertices")

    def test_color_path(self):
        """Color a path graph."""
        # Create path: 0-1-2-3
        edges = [(0, 1), (1, 2), (2, 3)]
        graph = Graph.from_edges(edges, num_vertices=4)

        colotab, colonbr = graph.color()

        # Verify function succeeded (only assertion from C test)
        assert colonbr > 0
        assert len(colotab) == 4

        # Print histogram like C test does
        color_counts = np.zeros(colonbr, dtype=np.int64)
        for color in colotab:
            color_counts[color] += 1

        print(f"\nPath graph: {colonbr} colors")
        for color_idx, count in enumerate(color_counts):
            print(f"  Color {color_idx}: {count} vertices")

    def test_color_grid_2x2(self):
        """Color a 2x2 grid graph."""
        # Create 2x2 grid:
        # 0 -- 1
        # |    |
        # 2 -- 3
        verttab = np.array([0, 2, 4, 6, 8], dtype=np.int64)
        edgetab = np.array([1, 2, 0, 3, 0, 3, 1, 2], dtype=np.int64)

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        colotab, colonbr = graph.color()

        # Verify function succeeded (only assertion from C test)
        assert colonbr > 0
        assert len(colotab) == 4

        # Print histogram like C test does
        color_counts = np.zeros(colonbr, dtype=np.int64)
        for color in colotab:
            color_counts[color] += 1

        print(f"\n2x2 Grid graph: {colonbr} colors")
        for color_idx, count in enumerate(color_counts):
            print(f"  Color {color_idx}: {count} vertices")

    def test_color_ring_histogram(self):
        """Test coloring a ring graph - matches C test histogram output."""
        # Create a ring graph like the C test would
        n = 10
        edges = [(i, (i + 1) % n) for i in range(n)]
        graph = Graph.from_edges(edges, num_vertices=n)

        colotab, colonbr = graph.color()

        # Verify function succeeded (only assertion from C test)
        assert colonbr > 0
        assert len(colotab) == n

        # Build color histogram (this is what the C test does)
        color_counts = np.zeros(colonbr, dtype=np.int64)
        for color in colotab:
            color_counts[color] += 1

        print(f"\nRing graph ({n} vertices): {colonbr} colors")
        for color_idx, count in enumerate(color_counts):
            print(f"  Color {color_idx}: {count} vertices")
