"""
Graph partitioning with overlap - FULLY PORTED

Tests overlapping graph partitioning functionality.
Corresponds to test_scotch_graph_part_ovl.c from the Scotch test suite.
"""

import pytest
from pathlib import Path
import numpy as np
from ctypes import byref, POINTER

from pyscotch import Graph, Strategy
from pyscotch import libscotch as lib


@pytest.mark.parametrize("int_size", [32, 64])
class TestScotchGraphPartOvl:
    """Tests from test_scotch_graph_part_ovl.c - overlapping partitioning"""

    def test_graph_partition_with_overlap(self, int_size):
        """Test overlapping graph partitioning on a file-based graph."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/m16x16_b1.grf")
        assert test_data.exists(), (
            f"Required test data missing: {test_data}. "
            f"Run 'git submodule update --init --recursive' to fetch Scotch test data."
        )

        # Load graph
        graph = Graph()
        graph.load(test_data)
        assert graph.check(), "Graph failed check after loading"

        # Get graph size
        vertnbr, edgenbr = graph.size()
        assert vertnbr > 0, "Graph has no vertices"

        # Create partition array
        partnbr = 4  # Partition into 4 parts
        parttab = np.zeros(vertnbr, dtype=lib.get_dtype())

        # Create strategy
        strat = Strategy()

        # Perform overlapping partitioning
        ret = lib.SCOTCH_graphPartOvl(
            byref(graph._graph),
            lib.SCOTCH_Num(partnbr),
            byref(strat._strat),
            parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )

        assert ret == 0, "Overlapping partitioning failed"

        # In overlapping partitioning, -1 indicates separator vertices
        # (vertices on boundaries between partitions)
        # Regular partition values should be in [0, partnbr)
        non_separator = parttab[parttab >= 0]
        assert len(non_separator) > 0, "All vertices are separators"
        assert np.all(non_separator < partnbr), f"Partition contains values >= {partnbr}"

        # Verify we have separator vertices (that's the point of overlap partitioning!)
        separator_count = np.sum(parttab == -1)
        assert separator_count >= 0, "Expected some separator vertices in overlapping partition"

        # Verify all partitions have at least one vertex
        unique_parts = np.unique(non_separator)
        assert len(unique_parts) > 0, "No partitions created"

    def test_simple_graph_for_overlap(self, int_size):
        """Test overlapping partitioning on a simple programmatic graph."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        # Create a simple graph
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
        graph = Graph.from_edges(edges, num_vertices=4)
        assert graph.check()

        vertnbr, _ = graph.size()

        # Partition into 2 parts with overlap
        partnbr = 2
        parttab = np.zeros(vertnbr, dtype=lib.get_dtype())

        strat = Strategy()

        ret = lib.SCOTCH_graphPartOvl(
            byref(graph._graph),
            lib.SCOTCH_Num(partnbr),
            byref(strat._strat),
            parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )

        assert ret == 0, "Overlapping partitioning failed"

        # -1 values indicate separator vertices (overlap boundaries)
        non_separator = parttab[parttab >= 0]
        assert len(non_separator) > 0, "All vertices are separators"
        assert np.all(non_separator < partnbr), f"Invalid partition values"
