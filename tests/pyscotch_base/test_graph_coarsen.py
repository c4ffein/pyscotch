"""
Tests for Graph coarsening methods: coarsen(), coarsen_match(), coarsen_build().
"""

from pyscotch import Graph


class TestGraphCoarsen:
    def test_coarsen_returns_smaller_graph(self, grid_4x4_graph):
        coarse, multi = grid_4x4_graph.coarsen()
        assert coarse is not None
        assert multi is not None
        cv, _ = coarse.size()
        fv, _ = grid_4x4_graph.size()
        assert 0 < cv <= fv

    def test_coarsen_too_small_returns_none(self):
        g = Graph.from_edges([(0, 1)], num_vertices=2)
        coarse, multi = g.coarsen(min_vertices=10)
        assert coarse is None
        assert multi is None

    def test_coarsen_match_and_build(self, hexagon_graph):
        coar_vertnbr, mate = hexagon_graph.coarsen_match()
        assert 0 < coar_vertnbr <= 6
        assert len(mate) == 6

        coarse, multi = hexagon_graph.coarsen_build(coar_vertnbr, mate)
        assert coarse.check()
        cv, _ = coarse.size()
        assert cv == coar_vertnbr

    def test_coarsen_check_passes(self, grid_4x4_graph):
        coarse, _ = grid_4x4_graph.coarsen()
        if coarse is not None:
            assert coarse.check()
