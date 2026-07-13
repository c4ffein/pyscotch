"""
Tests for Context class.
"""

import numpy as np
import pytest

from pyscotch import Context, random_seed, random_reset

# Context option indices, from SCOTCH_OPTIONNUM* in Scotch's library.h
OPTION_DETERMINISTIC = 0
OPTION_RANDOM_FIXED_SEED = 1


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


class TestContextOptions:
    def test_defaults_are_boolean_flags(self):
        ctx = Context()
        # Both known options are 0/1 flags (defaults may come from the
        # SCOTCH_DETERMINISTIC / SCOTCH_RANDOM_FIXED_SEED environment)
        assert ctx.option_get(OPTION_DETERMINISTIC) in (0, 1)
        assert ctx.option_get(OPTION_RANDOM_FIXED_SEED) in (0, 1)

    def test_set_get_roundtrip(self):
        ctx = Context()
        for option in (OPTION_DETERMINISTIC, OPTION_RANDOM_FIXED_SEED):
            for value in (1, 0):
                ctx.option_set(option, value)
                assert ctx.option_get(option) == value

    def test_options_are_per_context(self):
        ctx1 = Context()
        ctx2 = Context()
        ctx1.option_set(OPTION_DETERMINISTIC, 1)
        ctx2.option_set(OPTION_DETERMINISTIC, 0)
        assert ctx1.option_get(OPTION_DETERMINISTIC) == 1
        assert ctx2.option_get(OPTION_DETERMINISTIC) == 0

    def test_get_invalid_option_raises(self):
        ctx = Context()
        with pytest.raises(RuntimeError):
            ctx.option_get(99)
        with pytest.raises(RuntimeError):
            ctx.option_get(-1)

    def test_set_invalid_option_raises(self):
        ctx = Context()
        with pytest.raises(RuntimeError):
            ctx.option_set(99, 1)


class TestContextRandomDeterminism:
    def _partition_with_seed(self, graph, seed):
        with Context() as ctx:
            ctx.random_seed(seed)
            ctx.random_reset()
            return ctx.bind_graph(graph).partition(4)

    def _partition_with_cloned_state(self, graph, seed):
        random_seed(seed)
        random_reset()
        with Context() as ctx:
            ctx.random_clone()
            return ctx.bind_graph(graph).partition(4)

    def test_same_seed_gives_same_partition(self, grid_4x4_graph):
        p1 = self._partition_with_seed(grid_4x4_graph, 42)
        p2 = self._partition_with_seed(grid_4x4_graph, 42)
        assert np.array_equal(p1, p2)
        assert len(p1) == 16
        assert p1.min() >= 0
        assert p1.max() < 4

    def test_clone_reproduces_global_state(self, grid_4x4_graph):
        # Warm-up run: the very first context-bound operation in a process
        # can differ while Scotch lazily initializes internal state
        self._partition_with_cloned_state(grid_4x4_graph, 7)

        p1 = self._partition_with_cloned_state(grid_4x4_graph, 7)
        p2 = self._partition_with_cloned_state(grid_4x4_graph, 7)
        assert np.array_equal(p1, p2)
        assert p1.min() >= 0
        assert p1.max() < 4
