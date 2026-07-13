"""
Tests for module-level functions: scotch_version, random_*, mem_*.
"""

from pyscotch import scotch_version, random_reset, random_seed, mem_cur, mem_max


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
