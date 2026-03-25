"""
Tests for advanced Graph methods: partition_fixed, partition_overlap, repart,
stat, base, ordering I/O, mapping I/O, tab I/O.
"""

import numpy as np
import tempfile
import os

from pyscotch import Graph, Architecture
from pyscotch import libscotch as lib


class TestPartitionFixed:
    def test_fixed_vertices_stay(self, grid_4x4_graph):
        scotch_dtype = lib.get_scotch_dtype()
        parttab = np.full(16, -1, dtype=scotch_dtype)
        parttab[0] = 0
        parttab[15] = 1

        result = grid_4x4_graph.partition_fixed(2, parttab)
        assert len(result) == 16
        assert result[0] == 0
        assert result[15] == 1
        assert result.min() >= 0
        assert result.max() < 2


class TestPartitionOverlap:
    def test_returns_valid_array(self, grid_4x4_graph):
        result = grid_4x4_graph.partition_overlap(2)
        assert len(result) == 16
        assert 0 in set(result) or 1 in set(result)


class TestRepart:
    def test_repart_from_existing(self, grid_4x4_graph):
        initial = grid_4x4_graph.partition(2)
        result = grid_4x4_graph.repart(2, initial)
        assert len(result) == 16
        assert result.min() >= 0
        assert result.max() < 2


class TestGraphStat:
    def test_degree_hexagon(self, hexagon_graph):
        s = hexagon_graph.stat()
        assert s['degrmin'] == 2
        assert s['degrmax'] == 2

    def test_degree_star(self):
        g = Graph.from_edges([(0, 1), (0, 2), (0, 3), (0, 4)], num_vertices=5)
        s = g.stat()
        assert s['degrmin'] == 1
        assert s['degrmax'] == 4


class TestGraphBase:
    def test_roundtrip(self, hexagon_graph):
        old = hexagon_graph.base(1)
        assert old == 0
        old = hexagon_graph.base(0)
        assert old == 1


class TestOrderingIO:
    def test_order_check_valid(self, hexagon_graph):
        perm, inv = hexagon_graph.order()
        assert hexagon_graph.order_check(perm, inv)

    def test_order_save(self, hexagon_graph):
        perm, inv = hexagon_graph.order()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.ord') as f:
            path = f.name
        try:
            hexagon_graph.order_save(path, perm, inv)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)


class TestTabIO:
    def test_tab_save_load_roundtrip(self, hexagon_graph):
        parttab = hexagon_graph.partition(2)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.tab') as f:
            path = f.name
        try:
            hexagon_graph.tab_save(path, parttab)
            loaded = hexagon_graph.tab_load(path)
            assert np.array_equal(parttab, loaded)
        finally:
            os.unlink(path)


class TestMappingIO:
    def test_map_save(self, hexagon_graph):
        parttab = hexagon_graph.partition(2)
        arch = Architecture.complete_graph(2)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.map') as f:
            path = f.name
        try:
            hexagon_graph.map_save(path, parttab, arch)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_map_view(self, hexagon_graph):
        parttab = hexagon_graph.partition(2)
        arch = Architecture.complete_graph(2)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.view') as f:
            path = f.name
        try:
            hexagon_graph.map_view(path, parttab, arch)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)
