"""
Unit tests for Mapping and Ordering classes (no Scotch library required).
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import os

from pyscotch.mapping import Mapping
from pyscotch.ordering import Ordering


class TestMapping:
    """Test Mapping class (doesn't require Scotch library)."""

    def test_mapping_creation(self):
        """Test creating a mapping from array."""
        partitions = np.array([0, 1, 2, 0, 1, 2], dtype=np.int64)
        mapping = Mapping(partitions)
        assert mapping is not None
        assert len(mapping) == 6

    def test_mapping_num_partitions(self):
        """Test getting number of partitions."""
        partitions = np.array([0, 0, 1, 1, 2, 2, 3, 3], dtype=np.int64)
        mapping = Mapping(partitions)
        assert mapping.num_partitions() == 4

    def test_mapping_get_partition(self):
        """Test getting vertices in a partition."""
        partitions = np.array([0, 1, 0, 1, 2], dtype=np.int64)
        mapping = Mapping(partitions)

        part0 = mapping.get_partition(0)
        part1 = mapping.get_partition(1)
        part2 = mapping.get_partition(2)

        assert list(part0) == [0, 2]
        assert list(part1) == [1, 3]
        assert list(part2) == [4]

    def test_mapping_balance_perfect(self):
        """Test balance calculation with perfect balance."""
        partitions = np.array([0, 0, 1, 1, 2, 2], dtype=np.int64)
        mapping = Mapping(partitions)
        assert mapping.balance() == 1.0

    def test_mapping_balance_unbalanced(self):
        """Test balance calculation with unbalanced partitions."""
        partitions = np.array([0, 0, 0, 0, 1, 2], dtype=np.int64)
        mapping = Mapping(partitions)
        balance = mapping.balance()
        assert balance > 1.0
        # 4 in partition 0, avg is 2, so balance is 4/2 = 2.0
        assert abs(balance - 2.0) < 0.01

    def test_mapping_get_partition_sizes(self):
        """Test getting partition sizes."""
        partitions = np.array([0, 0, 0, 1, 1, 2], dtype=np.int64)
        mapping = Mapping(partitions)
        sizes = mapping.get_partition_sizes()

        assert len(sizes) == 3
        assert sizes[0] == 3
        assert sizes[1] == 2
        assert sizes[2] == 1

    def test_mapping_getitem(self):
        """Test indexing into mapping."""
        partitions = np.array([2, 1, 0, 2, 1], dtype=np.int64)
        mapping = Mapping(partitions)

        assert mapping[0] == 2
        assert mapping[1] == 1
        assert mapping[2] == 0
        assert mapping[3] == 2
        assert mapping[4] == 1

    def test_mapping_save_load(self):
        """Test saving and loading mappings."""
        partitions = np.array([0, 1, 2, 0, 1, 2], dtype=np.int64)
        mapping = Mapping(partitions)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.map') as f:
            temp_path = f.name

        try:
            mapping.save(temp_path)

            # Load and verify
            loaded = Mapping.load(temp_path)
            assert len(loaded) == len(mapping)
            assert loaded.num_partitions() == mapping.num_partitions()
            assert np.array_equal(loaded.mapping, mapping.mapping)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_mapping_repr(self):
        """Test string representation."""
        partitions = np.array([0, 0, 1, 1], dtype=np.int64)
        mapping = Mapping(partitions)
        repr_str = repr(mapping)

        assert "Mapping" in repr_str
        assert "size=4" in repr_str
        assert "num_partitions=2" in repr_str
        assert "balance" in repr_str


class TestOrdering:
    """Test Ordering class (doesn't require Scotch library)."""

    def test_ordering_creation(self):
        """Test creating an ordering."""
        perm = np.array([2, 0, 1, 3], dtype=np.int64)
        ordering = Ordering(perm)
        assert ordering is not None
        assert len(ordering) == 4

    def test_ordering_with_inverse(self):
        """Test creating ordering with inverse."""
        perm = np.array([1, 2, 0], dtype=np.int64)
        inv = np.array([2, 0, 1], dtype=np.int64)
        ordering = Ordering(perm, inv)

        assert np.array_equal(ordering.permutation, perm)
        assert np.array_equal(ordering.inverse_permutation, inv)

    def test_ordering_auto_inverse(self):
        """Test automatic inverse computation."""
        perm = np.array([2, 0, 3, 1], dtype=np.int64)
        ordering = Ordering(perm)

        # Verify inverse is correct
        for i in range(len(perm)):
            assert ordering.inverse_permutation[perm[i]] == i

    def test_ordering_apply(self):
        """Test applying ordering to array."""
        perm = np.array([2, 0, 1], dtype=np.int64)
        ordering = Ordering(perm)

        data = np.array([10, 20, 30])
        reordered = ordering.apply(data)

        assert np.array_equal(reordered, np.array([30, 10, 20]))

    def test_ordering_apply_inverse(self):
        """Test applying inverse ordering."""
        perm = np.array([2, 0, 1], dtype=np.int64)
        ordering = Ordering(perm)

        data = np.array([10, 20, 30])
        reordered = ordering.apply(data)
        restored = ordering.apply_inverse(reordered)

        assert np.array_equal(restored, data)

    def test_ordering_roundtrip(self):
        """Test that apply and apply_inverse are inverses."""
        perm = np.array([3, 1, 4, 0, 2], dtype=np.int64)
        ordering = Ordering(perm)

        original = np.array([100, 200, 300, 400, 500])

        # Apply and then inverse should give original
        reordered = ordering.apply(original)
        restored = ordering.apply_inverse(reordered)

        assert np.array_equal(restored, original)

    def test_ordering_getitem(self):
        """Test indexing into ordering."""
        perm = np.array([2, 0, 1], dtype=np.int64)
        ordering = Ordering(perm)

        assert ordering[0] == 2
        assert ordering[1] == 0
        assert ordering[2] == 1

    def test_ordering_save_load(self):
        """Test saving and loading orderings."""
        perm = np.array([2, 0, 3, 1], dtype=np.int64)
        ordering = Ordering(perm)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ord') as f:
            temp_path = f.name

        try:
            ordering.save(temp_path)

            # Load and verify
            loaded = Ordering.load(temp_path)
            assert len(loaded) == len(ordering)
            assert np.array_equal(loaded.permutation, ordering.permutation)
            assert np.array_equal(loaded.inverse_permutation, ordering.inverse_permutation)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_ordering_repr(self):
        """Test string representation."""
        perm = np.array([1, 0, 2], dtype=np.int64)
        ordering = Ordering(perm)
        repr_str = repr(ordering)

        assert "Ordering" in repr_str
        assert "size=3" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
