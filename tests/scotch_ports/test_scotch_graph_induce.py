"""
Ported from: external/scotch/src/check/test_scotch_graph_induce.c

Graph induction/subgraphs
"""

import pytest
import numpy as np
from pathlib import Path

from pyscotch import Graph
from pyscotch import libscotch as lib


class TestScotchGraphInduce:
    """Tests from test_scotch_graph_induce.c"""

    def test_induce_list_simple(self):
        """Test SCOTCH_graphInduceList on a simple graph."""
        # Create a simple graph: 0-1-2-3-4 (path)
        edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
        graph = Graph.from_edges(edges, num_vertices=5)

        # Induce subgraph with vertices [0, 2, 4]
        vertex_list = np.array([0, 2, 4], dtype=np.int64)
        induced = graph.induce_list(vertex_list)

        # Verify induced graph is valid
        assert induced.check(), "Induced graph failed SCOTCH_graphCheck"

        # Verify size (should have 3 vertices, 0 edges since they're not adjacent)
        vertnbr, edgenbr = induced.size()
        assert vertnbr == 3
        # No edges because 0, 2, 4 are not adjacent in original graph
        assert edgenbr == 0

    def test_induce_list_with_edges(self):
        """Test SCOTCH_graphInduceList preserves edges."""
        # Create triangle: 0-1-2-0
        edges = [(0, 1), (1, 2), (2, 0)]
        graph = Graph.from_edges(edges, num_vertices=3)

        # Induce subgraph with all vertices
        vertex_list = np.array([0, 1, 2], dtype=np.int64)
        induced = graph.induce_list(vertex_list)

        # Verify induced graph is valid
        assert induced.check(), "Induced graph failed SCOTCH_graphCheck"

        # Should preserve all vertices and edges
        vertnbr, edgenbr = induced.size()
        assert vertnbr == 3
        assert edgenbr == 6  # Each undirected edge becomes 2 directed

    def test_induce_list_partial_triangle(self):
        """Test inducing a subset of triangle vertices."""
        # Create triangle: 0-1-2-0
        edges = [(0, 1), (1, 2), (2, 0)]
        graph = Graph.from_edges(edges, num_vertices=3)

        # Induce subgraph with only vertices [0, 1]
        vertex_list = np.array([0, 1], dtype=np.int64)
        induced = graph.induce_list(vertex_list)

        # Verify induced graph is valid
        assert induced.check(), "Induced graph failed SCOTCH_graphCheck"

        # Should have 2 vertices and edge 0-1
        vertnbr, edgenbr = induced.size()
        assert vertnbr == 2
        assert edgenbr == 2  # Undirected edge 0-1 becomes 2 directed

    def test_induce_part_simple(self):
        """Test SCOTCH_graphInducePart on a simple graph."""
        # Create a graph: 0-1-2-3-4 (path)
        edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
        graph = Graph.from_edges(edges, num_vertices=5)

        # Create partition: vertices 0,1 in part 0; vertices 2,3,4 in part 1
        partition = np.array([0, 0, 1, 1, 1], dtype=np.int64)

        # Induce subgraph for partition 0 (vertices 0, 1)
        induced = graph.induce_part(partition, part_id=0)

        # Verify induced graph is valid
        assert induced.check(), "Induced graph failed SCOTCH_graphCheck (part 0)"

        # Should have 2 vertices and edge 0-1
        vertnbr, edgenbr = induced.size()
        assert vertnbr == 2
        assert edgenbr == 2  # Edge 0-1

        # Induce subgraph for partition 1 (vertices 2, 3, 4)
        induced = graph.induce_part(partition, part_id=1)

        # Verify induced graph is valid
        assert induced.check(), "Induced graph failed SCOTCH_graphCheck (part 1)"

        # Should have 3 vertices and edges 2-3, 3-4
        vertnbr, edgenbr = induced.size()
        assert vertnbr == 3
        assert edgenbr == 4  # Two edges: 2-3 and 3-4

    def test_induce_part_grid(self):
        """Test inducing partition from 2x2 grid."""
        # Create 2x2 grid:
        # 0 -- 1
        # |    |
        # 2 -- 3
        verttab = np.array([0, 2, 4, 6, 8], dtype=np.int64)
        edgetab = np.array([1, 2, 0, 3, 0, 3, 1, 2], dtype=np.int64)

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        # Partition: {0, 2} vs {1, 3}
        partition = np.array([0, 1, 0, 1], dtype=np.int64)

        # Induce part 0: vertices 0, 2 (edge 0-2)
        induced = graph.induce_part(partition, part_id=0)

        assert induced.check(), "Induced graph failed SCOTCH_graphCheck"
        vertnbr, edgenbr = induced.size()
        assert vertnbr == 2
        assert edgenbr == 2  # Edge 0-2

        # Induce part 1: vertices 1, 3 (edge 1-3)
        induced = graph.induce_part(partition, part_id=1)

        assert induced.check(), "Induced graph failed SCOTCH_graphCheck"
        vertnbr, edgenbr = induced.size()
        assert vertnbr == 2
        assert edgenbr == 2  # Edge 1-3
