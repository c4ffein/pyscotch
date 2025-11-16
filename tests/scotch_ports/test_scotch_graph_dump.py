"""
Ported from: external/scotch/src/check/test_scotch_graph_dump.c

Graph save/load operations (FILE* I/O)

The C test loads a graph from file and saves it back. We now support this
using our C compatibility layer (libpyscotch_compat.so) which is compiled
with the SAME toolchain as Scotch, avoiding FILE* pointer incompatibility issues.

This test verifies the save/load roundtrip works correctly.
"""

import pytest
import tempfile
import os
from pathlib import Path
import numpy as np

from pyscotch import Graph
from pyscotch import libscotch as lib

@pytest.fixture(autouse=True, scope="module")
def ensure_variant():
    """Sequential Scotch only (not PT-Scotch)."""
    variant = lib.get_active_variant()
    if variant:
        lib.set_active_variant(variant.int_size, parallel=False)

class TestScotchGraphDump:
    """Tests from test_scotch_graph_dump.c - now WORKING with compat layer!"""

    def test_save_load_roundtrip_simple(self):
        """Test saving and loading a simple graph (C test main functionality).

        Creates a graph programmatically, saves it to a file, loads it back,
        and verifies the roundtrip preserves the graph structure.
        """
        # Create a simple triangle graph
        edges = [(0, 1), (1, 2), (2, 0)]
        graph1 = Graph.from_edges(edges, num_vertices=3)

        v1, e1 = graph1.size()
        assert v1 == 3
        assert e1 == 6  # Each edge counted twice (undirected)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.grf', delete=False) as f:
            temp_file = f.name

        try:
            # Save using our compat layer
            graph1.save(temp_file)

            # Verify file was created
            assert os.path.exists(temp_file)
            assert os.path.getsize(temp_file) > 0

            # Load using our compat layer
            graph2 = Graph()
            graph2.load(temp_file)

            # Verify loaded graph matches
            v2, e2 = graph2.size()
            assert v2 == v1, f"Vertex count mismatch: {v2} != {v1}"
            assert e2 == e1, f"Edge count mismatch: {e2} != {e1}"

            # Both graphs should pass check
            assert graph1.check()
            assert graph2.check()

        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_save_load_from_scotch_data(self):
        """Test save/load with a graph built from Scotch data arrays."""
        # Build a simple chain: 0-1-2-3
        # verttab[i] = starting index in edgetab for vertex i's neighbors
        # For chain 0-1-2-3:
        #   vertex 0: neighbor [1]        -> edgetab[0:1]
        #   vertex 1: neighbors [0, 2]    -> edgetab[1:3]
        #   vertex 2: neighbors [1, 3]    -> edgetab[3:5]
        #   vertex 3: neighbor [2]        -> edgetab[5:6]
        scotch_dtype = lib.get_scotch_dtype()
        verttab = np.array([0, 1, 3, 5, 6], dtype=scotch_dtype)
        edgetab = np.array([1, 0, 2, 1, 3, 2], dtype=scotch_dtype)

        graph1 = Graph()
        graph1.build(baseval=0, verttab=verttab, edgetab=edgetab)

        # Verify it's valid
        assert graph1.check()
        v1, e1 = graph1.size()
        assert v1 == 4
        assert e1 == 6

        # Save and load
        with tempfile.NamedTemporaryFile(mode='w', suffix='.grf', delete=False) as f:
            temp_file = f.name

        try:
            graph1.save(temp_file)

            graph2 = Graph()
            graph2.load(temp_file)

            # Verify match
            assert graph2.check()
            v2, e2 = graph2.size()
            assert v2 == v1
            assert e2 == e1

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_save_load_larger_graph(self):
        """Test save/load with a larger, more complex graph."""
        # Create a 3x3 grid graph
        edges = [
            # Row 0
            (0, 1), (1, 2),
            # Row 1
            (3, 4), (4, 5),
            # Row 2
            (6, 7), (7, 8),
            # Columns
            (0, 3), (3, 6),
            (1, 4), (4, 7),
            (2, 5), (5, 8),
        ]
        graph1 = Graph.from_edges(edges, num_vertices=9)

        v1, e1 = graph1.size()
        assert v1 == 9
        assert e1 == 24  # 12 edges * 2 (undirected)

        # Save and load
        with tempfile.NamedTemporaryFile(mode='w', suffix='.grf', delete=False) as f:
            temp_file = f.name

        try:
            graph1.save(temp_file)

            graph2 = Graph()
            graph2.load(temp_file)

            assert graph2.check()
            v2, e2 = graph2.size()
            assert v2 == v1
            assert e2 == e1

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
