"""
Mesh to graph conversion - FULLY PORTED

Tests the conversion of Scotch mesh structures to graph structures.
Corresponds to test_scotch_mesh_graph.c from the Scotch test suite.
"""

import pytest
from pathlib import Path

from pyscotch import libscotch as lib
from pyscotch import Graph, Mesh


@pytest.mark.parametrize("int_size", [32, 64])
class TestScotchMeshGraph:
    """Tests from test_scotch_mesh_graph.c - mesh to graph conversion"""

    def test_mesh_to_graph_conversion(self, int_size):
        """Test loading a mesh from file and converting it to a graph."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/small2.msh")
        if not test_data.exists():
            pytest.skip(f"Test data file not found: {test_data}")

        # Initialize and load mesh
        mesh = Mesh()
        mesh.load(test_data)

        # Convert mesh to graph
        graph = mesh.to_graph()

        # Verify the resulting graph is valid
        assert graph.check(), "Converted graph failed consistency check"

        # Verify the graph has vertices (mesh was not empty)
        vertnbr, edgenbr = graph.size()
        assert vertnbr > 0, "Graph has no vertices"
        assert edgenbr > 0, "Graph has no edges"

    def test_basic_graph_creation(self, int_size):
        """Test basic graph creation (doesn't require mesh)."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        edges = [(0, 1), (1, 2), (2, 0)]
        graph = Graph.from_edges(edges, num_vertices=3)
        assert graph.check()
