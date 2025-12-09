"""
Ported from: external/scotch/src/check/test_multilib.c

Graph loading test using the current Scotch variant.

Single-Variant Design:
Tests run with ONE Scotch variant, configured via environment variables:
- PYSCOTCH_INT_SIZE: 32 or 64 (default: 32)
- PYSCOTCH_PARALLEL: 0 or 1 (default: 0)

For multi-library coexistence verification (loading both 32-bit and 64-bit
libraries simultaneously), see tests/pyscotch_base/test_symbol_prefixes.py.
"""

from pathlib import Path

from pyscotch import Graph


class TestGraphLoading:
    """Tests from test_multilib.c - graph loading"""

    def test_load_graph_from_file(self):
        """Test loading graph from Scotch test data file.

        This verifies that PyScotch can correctly load a graph file
        and the graph passes validation checks.
        """
        test_data = Path("external/scotch/src/check/data/m4x4_b1.grf")

        assert test_data.exists(), (
            f"Required test data missing: {test_data}. "
            f"Run 'git submodule update --init --recursive' to fetch Scotch test data."
        )

        # Load with current variant
        graph = Graph()
        graph.load(test_data)

        # Verify graph
        assert graph.check(), "Graph failed check"
        vertnbr, edgenbr = graph.size()
        assert vertnbr > 0, "Graph has no vertices"
        assert edgenbr > 0, "Graph has no edges"

        # Expected values for m4x4_b1.grf (4x4 mesh)
        assert vertnbr == 16, f"Expected 16 vertices, got {vertnbr}"

    def test_graph_from_edges(self):
        """Test creating a graph programmatically."""
        edges = [(0, 1), (1, 2), (2, 0)]

        graph = Graph.from_edges(edges, num_vertices=3)

        # Verify
        vertnbr, edgenbr = graph.size()
        assert vertnbr == 3
        assert edgenbr == 6  # Each undirected edge counted twice
        assert graph.check()
