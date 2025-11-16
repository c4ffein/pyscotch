"""
Graph mapping and remapping - FULLY PORTED

Tests graph mapping computation and remapping operations.
Corresponds to test_scotch_graph_map_copy.c from the Scotch test suite.
"""

import pytest
from pathlib import Path
import numpy as np
from ctypes import byref, POINTER

from pyscotch import Graph, Architecture, Strategy
from pyscotch import libscotch as lib


@pytest.mark.parametrize("int_size", [32, 64])
class TestScotchGraphMapCopy:
    """Tests from test_scotch_graph_map_copy.c - mapping and remapping"""

    def test_graph_mapping(self, int_size):
        """Test basic graph mapping computation."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/m4x4_b1.grf")
        if not test_data.exists():
            pytest.skip(f"Test data file not found: {test_data}")

        # Load graph
        graph = Graph()
        graph.load(test_data)
        assert graph.check()

        vertnbr, _ = graph.size()
        assert vertnbr > 0

        # Create architecture (complete graph with 5 nodes)
        arch = Architecture.complete_graph(5)

        # Create partition array
        parttab = np.zeros(vertnbr, dtype=lib.get_dtype())

        # Create mapping structure
        mapping = lib.SCOTCH_Mapping()

        # Initialize mapping
        ret = lib.SCOTCH_graphMapInit(
            byref(graph._graph),
            byref(mapping),
            byref(arch._arch),
            parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )
        assert ret == 0, "graphMapInit failed"

        # Create strategy for mapping
        strat = Strategy()

        # Compute mapping
        ret = lib.SCOTCH_graphMapCompute(
            byref(graph._graph),
            byref(mapping),
            byref(strat._strat)
        )
        assert ret == 0, "graphMapCompute failed"

        # Verify partition values are valid
        assert np.all(parttab >= 0), "Partition has negative values"
        assert np.all(parttab < 5), "Partition has values >= 5"

        # Cleanup
        lib.SCOTCH_graphMapExit(byref(graph._graph), byref(mapping))

    def test_graph_remapping(self, int_size):
        """Test graph remapping from an old partition to a new one."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/m4x4_b1.grf")
        if not test_data.exists():
            pytest.skip(f"Test data file not found: {test_data}")

        # Load graph
        graph = Graph()
        graph.load(test_data)
        vertnbr, _ = graph.size()

        # Create architecture
        arch = Architecture.complete_graph(5)

        # Create partition arrays for old and new mappings
        parttab_new = np.zeros(vertnbr, dtype=lib.get_dtype())
        parttab_old = np.zeros(vertnbr, dtype=lib.get_dtype())

        # Create mapping structures
        mapping_new = lib.SCOTCH_Mapping()
        mapping_old = lib.SCOTCH_Mapping()

        # Initialize and compute initial mapping
        ret = lib.SCOTCH_graphMapInit(
            byref(graph._graph),
            byref(mapping_new),
            byref(arch._arch),
            parttab_new.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )
        assert ret == 0, "graphMapInit (new) failed"

        strat = Strategy()
        ret = lib.SCOTCH_graphMapCompute(
            byref(graph._graph),
            byref(mapping_new),
            byref(strat._strat)
        )
        assert ret == 0, "graphMapCompute failed"

        # Copy new mapping to old mapping for remapping test
        np.copyto(parttab_old, parttab_new)

        # Exit the new mapping to prepare for remapping
        lib.SCOTCH_graphMapExit(byref(graph._graph), byref(mapping_new))

        # Re-initialize for remapping
        mapping_new = lib.SCOTCH_Mapping()
        ret = lib.SCOTCH_graphMapInit(
            byref(graph._graph),
            byref(mapping_new),
            byref(arch._arch),
            parttab_new.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )
        assert ret == 0, "graphMapInit (remap) failed"

        # Initialize old mapping
        ret = lib.SCOTCH_graphMapInit(
            byref(graph._graph),
            byref(mapping_old),
            byref(arch._arch),
            parttab_old.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )
        assert ret == 0, "graphMapInit (old) failed"

        # Compute remapping
        ret = lib.SCOTCH_graphRemapCompute(
            byref(graph._graph),
            byref(mapping_new),
            byref(mapping_old),
            0.0,  # remapping cost parameter
            None,  # No vertex permutation
            byref(strat._strat)
        )
        assert ret == 0, "graphRemapCompute failed"

        # Verify the new partition is valid
        assert np.all(parttab_new >= 0), "New partition has negative values"
        assert np.all(parttab_new < 5), "New partition has values >= 5"

        # Cleanup
        lib.SCOTCH_graphMapExit(byref(graph._graph), byref(mapping_old))
        lib.SCOTCH_graphMapExit(byref(graph._graph), byref(mapping_new))

    def test_graph_from_edges_for_mapping(self, int_size):
        """Test mapping on a programmatically created graph."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        # Create a simple graph
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
        graph = Graph.from_edges(edges, num_vertices=4)
        assert graph.check()

        vertnbr, _ = graph.size()

        # Create architecture
        arch = Architecture.complete_graph(3)

        # Create partition array
        parttab = np.zeros(vertnbr, dtype=lib.get_dtype())

        # Create and initialize mapping
        mapping = lib.SCOTCH_Mapping()
        ret = lib.SCOTCH_graphMapInit(
            byref(graph._graph),
            byref(mapping),
            byref(arch._arch),
            parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )
        assert ret == 0, "graphMapInit failed"

        # Compute mapping
        strat = Strategy()
        ret = lib.SCOTCH_graphMapCompute(
            byref(graph._graph),
            byref(mapping),
            byref(strat._strat)
        )
        assert ret == 0, "graphMapCompute failed"

        # Verify
        assert np.all(parttab >= 0) and np.all(parttab < 3)

        # Cleanup
        lib.SCOTCH_graphMapExit(byref(graph._graph), byref(mapping))
