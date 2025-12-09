"""
Ported from: external/scotch/src/check/test_scotch_graph_coarsen.c

Graph coarsening (multilevel coarsening) tests.

The C test loads a graph from file and performs 3 coarsening passes:
1. SCOTCH_graphCoarsenMatch + SCOTCH_graphCoarsenBuild (two-step)
2. Custom matching + SCOTCH_graphCoarsenBuild (manual matching)
3. SCOTCH_graphCoarsen (all-in-one convenience function)

Since we can't load from files (FILE* issues), we create test graphs directly.
"""

import pytest
import numpy as np
from ctypes import byref, POINTER

from pyscotch import Graph, SCOTCH_COARSENNONE, SCOTCH_COARSENNOMERGE
from pyscotch import libscotch as lib


class TestScotchGraphCoarsen:
    """Tests from test_scotch_graph_coarsen.c"""

    def test_coarsen_match_and_build(self):
        """Test SCOTCH_graphCoarsenMatch + SCOTCH_graphCoarsenBuild (C test lines 274-283).

        Matches C test's first coarsening pass using the two-step approach:
        1. Compute matching with SCOTCH_graphCoarsenMatch
        2. Build coarse graph with SCOTCH_graphCoarsenBuild
        """
        # Create a simple test graph: 0-1-2-3-4 (chain of 5 vertices)
        edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
        fine_graph = Graph.from_edges(edges, num_vertices=5)

        fine_vertnbr = fine_graph.size()[0]

        # Allocate mate array
        scotch_dtype = lib.get_scotch_dtype()
        mate_array = np.zeros(fine_vertnbr, dtype=scotch_dtype)
        mate_array_c = mate_array.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Compute matching (C test line 274)
        coar_vertnbr = lib.SCOTCH_Num(0)  # Minimum coarse vertices
        ret = lib.SCOTCH_graphCoarsenMatch(
            byref(fine_graph._graph),
            byref(coar_vertnbr),
            1.0,  # ratio
            SCOTCH_COARSENNOMERGE,
            mate_array_c
        )
        assert ret == 0, "SCOTCH_graphCoarsenMatch failed"

        # Verify coarsening happened (C test lines 281-283)
        assert coar_vertnbr.value > 0, "No coarse vertices created"
        assert coar_vertnbr.value <= fine_vertnbr, "More coarse than fine vertices"

        # Coarsening ratio should be reasonable (C test prints ratio)
        ratio = coar_vertnbr.value / fine_vertnbr
        print(f"Graph mated with ratio: {ratio}")
        assert 0 < ratio <= 1.0, f"Invalid ratio: {ratio}"

        # Allocate multinode array (C test line 285)
        multinode_array = np.zeros(coar_vertnbr.value * 2, dtype=scotch_dtype)
        multinode_array_c = multinode_array.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Build coarse graph (C test line 290)
        coarse_graph = Graph()
        ret = lib.SCOTCH_graphCoarsenBuild(
            byref(fine_graph._graph),
            coar_vertnbr,
            mate_array_c,
            byref(coarse_graph._graph),
            multinode_array_c
        )
        assert ret == 0, "SCOTCH_graphCoarsenBuild failed"

        # Verify coarse graph (C test lines 295-300)
        assert coarse_graph.check(), "Coarse graph failed SCOTCH_graphCheck"
        coarse_vertnbr, coarse_edgenbr = coarse_graph.size()
        print(f"Coarse graph: {coarse_vertnbr} vertices, {coarse_edgenbr} edges")
        print(f"Graph coarsened with ratio: {coarse_vertnbr / fine_vertnbr}")

        assert coarse_vertnbr <= fine_vertnbr, "Coarse graph larger than fine"

    def test_coarsen_all_in_one(self):
        """Test SCOTCH_graphCoarsen all-in-one function (C test lines 338-349).

        Matches C test's third coarsening pass using the convenience function
        that combines matching and building in one call.
        """
        # Create a simple test graph
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]  # Hexagon
        fine_graph = Graph.from_edges(edges, num_vertices=6)

        fine_vertnbr = fine_graph.size()[0]
        scotch_dtype = lib.get_scotch_dtype()

        # Allocate multinode array (C test line 333)
        multinode_array = np.zeros(fine_vertnbr * 2, dtype=scotch_dtype)
        multinode_array_c = multinode_array.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Coarsen graph with all-in-one function (C test line 338)
        coarse_graph = Graph()
        ret = lib.SCOTCH_graphCoarsen(
            byref(fine_graph._graph),
            lib.SCOTCH_Num(1),  # minimum coarse vertices
            1.0,  # ratio
            SCOTCH_COARSENNONE,
            byref(coarse_graph._graph),
            multinode_array_c
        )
        assert ret == 0, "SCOTCH_graphCoarsen failed"

        # Verify coarse graph (C test lines 343-347)
        assert coarse_graph.check(), "Coarse graph failed SCOTCH_graphCheck"
        coarse_vertnbr, coarse_edgenbr = coarse_graph.size()
        print(f"Coarse graph: {coarse_vertnbr} vertices, {coarse_edgenbr} edges")
        print(f"Graph coarsened with ratio: {coarse_vertnbr / fine_vertnbr}")

        assert coarse_vertnbr > 0, "No coarse vertices created"
        assert coarse_vertnbr <= fine_vertnbr, "Coarse graph larger than fine"

    def test_coarsen_with_various_graphs(self):
        """Test coarsening on various graph topologies.

        Not in C test, but ensures coarsening works on different structures.
        """
        test_cases = [
            ("Triangle", [(0, 1), (1, 2), (2, 0)], 3),
            ("Star", [(0, 1), (0, 2), (0, 3), (0, 4)], 5),
            ("Complete-4", [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], 4),
        ]

        for name, edges, num_verts in test_cases:
            graph = Graph.from_edges(edges, num_vertices=num_verts)
            fine_vertnbr = graph.size()[0]

            # Use all-in-one coarsen function
            scotch_dtype = lib.get_scotch_dtype()
            multinode_array = np.zeros(fine_vertnbr * 2, dtype=scotch_dtype)
            multinode_array_c = multinode_array.ctypes.data_as(POINTER(lib.SCOTCH_Num))

            coarse_graph = Graph()
            ret = lib.SCOTCH_graphCoarsen(
                byref(graph._graph),
                lib.SCOTCH_Num(1),
                1.0,
                SCOTCH_COARSENNONE,
                byref(coarse_graph._graph),
                multinode_array_c
            )

            assert ret == 0, f"SCOTCH_graphCoarsen failed for {name}"
            assert coarse_graph.check(), f"Coarse graph check failed for {name}"

            coarse_vertnbr = coarse_graph.size()[0]
            ratio = coarse_vertnbr / fine_vertnbr
            print(f"{name}: {fine_vertnbr} -> {coarse_vertnbr} vertices (ratio={ratio:.2f})")

            assert coarse_vertnbr <= fine_vertnbr, f"{name}: coarse > fine"
