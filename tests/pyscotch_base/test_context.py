"""
Tests for Context class.
"""

import os

import numpy as np
import pytest

from pyscotch import Context, random_reset, random_seed

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
        # Closed explicitly: binding starts Scotch's thread pool, which pins
        # the CALLING thread to one core (common_thread.c threadCreate) and
        # only unpins it in SCOTCH_contextExit. A leaked Context leaves the
        # whole pytest process -- and every mpirun it spawns afterwards --
        # confined to a single CPU.
        with Context() as ctx:
            bound = ctx.bind_graph(hexagon_graph)
            assert bound.size() == hexagon_graph.size()

    @pytest.mark.skipif(not hasattr(os, "sched_getaffinity"), reason="no CPU affinity API")
    def test_closed_context_gives_the_cpus_back(self, grid_4x4_graph):
        """Whatever the thread pool does to the calling thread's CPU affinity
        while a Context is alive, closing it must restore the process to the
        CPU set it had before -- the leak that confined whole test sessions,
        and every mpirun they spawned, to one core."""
        before = os.sched_getaffinity(0)
        with Context() as ctx:
            parts = ctx.bind_graph(grid_4x4_graph).partition(4)
        assert len(parts) == 16
        assert os.sched_getaffinity(0) == before


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
