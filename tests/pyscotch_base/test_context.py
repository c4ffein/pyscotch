"""
Tests for Context class.
"""

from pyscotch import Context


class TestContext:
    def test_create_destroy(self):
        ctx = Context()
        assert ctx is not None

    def test_random_seed(self):
        ctx = Context()
        ctx.random_seed(42)

    def test_random_clone_and_reset(self):
        ctx = Context()
        ctx.random_clone()
        ctx.random_reset()

    def test_bind_graph(self, hexagon_graph):
        ctx = Context()
        bound = ctx.bind_graph(hexagon_graph)
        assert bound.size() == hexagon_graph.size()
