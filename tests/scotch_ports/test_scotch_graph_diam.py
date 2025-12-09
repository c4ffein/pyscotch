"""
Ported from: external/scotch/src/check/test_scotch_graph_diam.c

Graph diameter computation tests.

The C test loads a graph from file and computes the pseudo-diameter using
SCOTCH_graphDiamPV(). Since we can't load from files (FILE* issues), we
create test graphs directly with known diameters.
"""

import pytest
from ctypes import byref

from pyscotch import Graph
from pyscotch import libscotch as lib


class TestScotchGraphDiam:
    """Tests from test_scotch_graph_diam.c"""

    def test_diam_chain_graph(self):
        """Test pseudo-diameter on a chain graph (C test line 105).

        A chain graph 0-1-2-3-4 has a diameter of 4 (distance from 0 to 4).
        Matches the C test's call to SCOTCH_graphDiamPV.
        """
        # Create a chain graph: 0-1-2-3-4
        edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
        graph = Graph.from_edges(edges, num_vertices=5)

        # Reset random state like C test (line 103)
        lib.SCOTCH_randomReset()

        # Compute pseudo-diameter (C test line 105)
        diam = lib.SCOTCH_graphDiamPV(byref(graph._graph))

        # Verify computation succeeded (C test line 105-108)
        assert diam >= 0, "SCOTCH_graphDiamPV failed (returned negative)"

        # Chain of 5 vertices has diameter 4 (longest path 0->4)
        print(f"Chain graph pseudo-diameter: {diam}")
        assert diam == 4, f"Expected diameter 4 for chain, got {diam}"

    def test_diam_cycle_graph(self):
        """Test pseudo-diameter on a cycle graph.

        A cycle (hexagon) has diameter equal to half the vertices (rounded down).
        For 6 vertices: diameter = 3.
        """
        # Create a cycle: 0-1-2-3-4-5-0
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]
        graph = Graph.from_edges(edges, num_vertices=6)

        lib.SCOTCH_randomReset()
        diam = lib.SCOTCH_graphDiamPV(byref(graph._graph))

        assert diam >= 0, "SCOTCH_graphDiamPV failed"
        print(f"Cycle graph pseudo-diameter: {diam}")

        # For a cycle of n vertices, diameter is floor(n/2)
        # For n=6, diameter = 3
        assert diam == 3, f"Expected diameter 3 for hexagon cycle, got {diam}"

    def test_diam_star_graph(self):
        """Test pseudo-diameter on a star graph.

        A star graph (center connected to all others) has diameter 2:
        any two non-center vertices are distance 2 apart (through center).
        """
        # Create a star: center 0 connected to 1, 2, 3, 4
        edges = [(0, 1), (0, 2), (0, 3), (0, 4)]
        graph = Graph.from_edges(edges, num_vertices=5)

        lib.SCOTCH_randomReset()
        diam = lib.SCOTCH_graphDiamPV(byref(graph._graph))

        assert diam >= 0, "SCOTCH_graphDiamPV failed"
        print(f"Star graph pseudo-diameter: {diam}")

        # Star has diameter 2 (any two leaf nodes are 2 apart via center)
        assert diam == 2, f"Expected diameter 2 for star graph, got {diam}"

    def test_diam_single_vertex(self):
        """Test pseudo-diameter on a single vertex graph.

        A single vertex has diameter 0 (no edges).
        """
        # Single vertex with no edges - use build directly
        import numpy as np
        scotch_dtype = lib.get_scotch_dtype()

        graph = Graph()
        verttab = np.array([0, 0], dtype=scotch_dtype)  # Single vertex, no edges
        edgetab = np.array([], dtype=scotch_dtype)  # No edges

        graph.build(
            baseval=0,
            verttab=verttab,
            edgetab=edgetab,
        )

        lib.SCOTCH_randomReset()
        diam = lib.SCOTCH_graphDiamPV(byref(graph._graph))

        assert diam >= 0, "SCOTCH_graphDiamPV failed"
        print(f"Single vertex pseudo-diameter: {diam}")

        # Single vertex should have diameter 0
        assert diam == 0, f"Expected diameter 0 for single vertex, got {diam}"

    def test_diam_complete_graph(self):
        """Test pseudo-diameter on a complete graph.

        Complete graph K4: every vertex connected to every other.
        Diameter = 1 (all vertices are 1 hop apart).
        """
        # Complete graph K4
        edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        graph = Graph.from_edges(edges, num_vertices=4)

        lib.SCOTCH_randomReset()
        diam = lib.SCOTCH_graphDiamPV(byref(graph._graph))

        assert diam >= 0, "SCOTCH_graphDiamPV failed"
        print(f"Complete graph K4 pseudo-diameter: {diam}")

        # Complete graph has diameter 1 (all vertices adjacent)
        assert diam == 1, f"Expected diameter 1 for complete graph, got {diam}"
