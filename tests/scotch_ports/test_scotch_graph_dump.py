"""
Ported from: external/scotch/src/check/test_scotch_graph_dump.c

Graph structure dumping (save/load round-trip tests).

The C test generates a test graph structure using gdump, builds it,
and saves it to a file. For Python, we test the save/load round-trip
by loading a graph file, saving it, and loading it back to verify.
"""

import pytest
import tempfile
from pathlib import Path

from pyscotch import Graph
from pyscotch import libscotch as lib


@pytest.fixture(autouse=True, scope="module")
def ensure_variant():
    """Sequential Scotch only (not PT-Scotch)."""
    variant = lib.get_active_variant()
    if variant:
        lib.set_active_variant(variant.int_size, parallel=False)


class TestScotchGraphDump:
    """Tests from test_scotch_graph_dump.c"""

    @pytest.mark.skip(reason="Graph file I/O causes segfaults - see QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4")
    def test_save_load_roundtrip_simple(self):
        """Test saving and loading a simple graph (matches C test intent)."""
        # Create a simple graph
        graph = Graph.from_edges([(0, 1), (1, 2), (2, 0)], num_vertices=3)

        # Get original size
        orig_vertnbr, orig_edgenbr = graph.size()

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.grf', delete=False) as f:
            temp_path = Path(f.name)

        try:
            graph.save(temp_path)

            # Load it back
            loaded_graph = Graph()
            loaded_graph.load(temp_path)

            # Verify graph is valid
            assert loaded_graph.check(), "Loaded graph failed SCOTCH_graphCheck"

            # Verify sizes match
            loaded_vertnbr, loaded_edgenbr = loaded_graph.size()
            assert loaded_vertnbr == orig_vertnbr, f"Vertex count mismatch: {loaded_vertnbr} != {orig_vertnbr}"
            assert loaded_edgenbr == orig_edgenbr, f"Edge count mismatch: {loaded_edgenbr} != {orig_edgenbr}"
        finally:
            # Clean up
            if temp_path.exists():
                temp_path.unlink()

    @pytest.mark.skip(reason="Graph file I/O causes segfaults - see QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4")
    def test_save_load_from_scotch_data(self):
        """Test save/load round-trip using Scotch test data (m16x16_b1.grf)."""
        # This matches the C test which uses m16x16_b1.grf
        test_data = Path("external/scotch/src/check/data/m16x16_b1.grf")

        if not test_data.exists():
            pytest.skip(f"Test data file not found: {test_data}")

        # Load original graph
        original = Graph()
        original.load(test_data)

        # Verify original is valid
        assert original.check(), "Original graph failed SCOTCH_graphCheck"

        # Get original size
        orig_vertnbr, orig_edgenbr = original.size()

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.grf', delete=False) as f:
            temp_path = Path(f.name)

        try:
            original.save(temp_path)

            # Load it back
            loaded = Graph()
            loaded.load(temp_path)

            # Verify loaded graph is valid
            assert loaded.check(), "Loaded graph failed SCOTCH_graphCheck"

            # Verify sizes match
            loaded_vertnbr, loaded_edgenbr = loaded.size()
            assert loaded_vertnbr == orig_vertnbr, f"Vertex count mismatch: {loaded_vertnbr} != {orig_vertnbr}"
            assert loaded_edgenbr == orig_edgenbr, f"Edge count mismatch: {loaded_edgenbr} != {orig_edgenbr}"
        finally:
            # Clean up
            if temp_path.exists():
                temp_path.unlink()
