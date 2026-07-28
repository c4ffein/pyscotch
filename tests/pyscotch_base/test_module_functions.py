"""
Tests for module-level functions: scotch_version, random_*, mem_*.
"""

import numpy as np

from pyscotch import Graph, random_proc, random_reset, random_seed, mem_cur, mem_max, scotch_version


class TestScotchVersion:
    def test_returns_tuple(self):
        v = scotch_version()
        assert len(v) == 3

    def test_reasonable_values(self):
        major, minor, patch = scotch_version()
        assert major >= 7
        assert minor >= 0
        assert patch >= 0


class TestRandom:
    def test_reset(self):
        random_reset()

    def test_seed(self):
        random_seed(12345)

    def test_seed_then_reset(self):
        random_seed(42)
        random_reset()

    def test_random_proc_decorrelates_and_roundtrips(self):
        """random_proc(n) folds a process number into the seed: after a reset
        the stream (and thus the partition) differs, and random_proc(0) then
        restores the default stream bit-for-bit.

        Uses a graph small enough to stay below Scotch's threading thresholds:
        threaded execution is scheduling-dependent, so on large graphs even
        identical PRNG state does not guarantee identical partitions.
        """

        def ring(n=64):
            vert = np.arange(0, 2 * n + 1, 2)
            edge = np.empty(2 * n, dtype=np.int64)
            for v in range(n):
                edge[2 * v] = (v - 1) % n
                edge[2 * v + 1] = (v + 1) % n
            g = Graph()
            g.build(vert.astype(np.int64), edge)
            return g

        random_reset()
        base = ring().partition(4)
        random_proc(7)
        random_reset()
        shifted = ring().partition(4)
        assert not np.array_equal(base, shifted), "random_proc(7) did not change the stream"
        random_proc(0)
        random_reset()
        restored = ring().partition(4)
        assert np.array_equal(base, restored), "random_proc(0) did not restore the default stream"


class TestMemory:
    def test_mem_cur_returns_int(self):
        assert isinstance(mem_cur(), int)

    def test_mem_max_returns_int(self):
        assert isinstance(mem_max(), int)

    def test_mem_values_consistent(self):
        # Without COMMON_MEMORY_TRACE, Scotch returns the -1 sentinel from
        # both routines; with it, both are byte counts and peak >= current.
        cur = mem_cur()
        peak = mem_max()
        if cur == -1:
            assert peak == -1
        else:
            assert 0 <= cur <= peak

    def test_mem_max_is_monotonic(self):
        from pyscotch import Graph

        before = mem_max()
        graphs = [
            Graph.from_edges([(i, i + 1) for i in range(99)], num_vertices=100)
            for _ in range(4)
        ]
        after = mem_max()
        assert len(graphs) == 4
        if before == -1:
            assert after == -1  # memory tracing not compiled in
        else:
            assert after >= before  # peak footprint never decreases
