"""
Ported from: external/scotch/src/check/test_scotch_graph_dump.c

Graph save/load operations (FILE* I/O)

The C test loads a graph from file and saves it back. We now support this
using C's fopen() instead of Python's file handling, avoiding FILE* pointer
incompatibility issues.

This test verifies the save/load roundtrip works correctly.
"""

import pytest
import tempfile
import os
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
    """Tests from test_scotch_graph_dump.c - now WORKING with C fopen()!"""

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
            # Save using C fopen()
            graph1.save(temp_file)

            # Verify file was created
            assert os.path.exists(temp_file)
            assert os.path.getsize(temp_file) > 0

            # Load using C fopen()
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
        """Test save/load with a graph built from Scotch data arrays.

        This tests that graphs created with build() (not from_edges())
        can also be saved and loaded correctly.
        """
        import numpy as np

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

        assert graph1.check()
        v1, e1 = graph1.size()

        # Save and load roundtrip
        with tempfile.NamedTemporaryFile(mode='w', suffix='.grf', delete=False) as f:
            temp_file = f.name

        try:
            graph1.save(temp_file)

            graph2 = Graph()
            graph2.load(temp_file)

            v2, e2 = graph2.size()
            assert v2 == v1
            assert e2 == e1
            assert graph2.check()

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_save_load_larger_graph(self):
        """Test save/load with a larger, more complex graph."""
        # Create a grid graph: 3x3 grid
        edges = []
        for i in range(3):
            for j in range(3):
                node = i * 3 + j
                # Right neighbor
                if j < 2:
                    edges.append((node, node + 1))
                # Bottom neighbor
                if i < 2:
                    edges.append((node, node + 3))

        graph1 = Graph.from_edges(edges, num_vertices=9)

        v1, e1 = graph1.size()
        assert v1 == 9

        with tempfile.NamedTemporaryFile(mode='w', suffix='.grf', delete=False) as f:
            temp_file = f.name

        try:
            graph1.save(temp_file)

            graph2 = Graph()
            graph2.load(temp_file)

            v2, e2 = graph2.size()
            assert v2 == v1
            assert e2 == e1
            assert graph2.check()

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
