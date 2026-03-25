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
