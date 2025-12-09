"""
Enhanced random number generation tests for PyScotch.

These are additional tests beyond what's in the Scotch C test suite,
providing more comprehensive coverage of the RNG functionality.

Single-Variant Design:
Tests run with ONE Scotch variant, configured via environment variables:
- PYSCOTCH_INT_SIZE: 32 or 64 (default: 32)
- PYSCOTCH_PARALLEL: 0 or 1 (default: 0)
"""

import pytest
from pyscotch import libscotch as lib


class TestRandomEnhanced:
    """Enhanced random number generation tests."""

    def test_random_basic_generation(self):
        """Test basic random number generation produces diverse values."""
        # Initialize RNG
        lib.SCOTCH_randomReset()

        # Generate random values
        values = []
        for _ in range(100):
            val = lib.SCOTCH_randomVal(1000)
            values.append(val)
            # Verify value is in range [0, 1000)
            assert 0 <= val < 1000, f"Random value {val} out of range [0, 1000)"

        # Verify we got some diversity (not all the same)
        unique_values = set(values)
        assert len(unique_values) > 10, "Random generator produced too few unique values"

    def test_random_seed_affects_sequence(self):
        """Test that SCOTCH_randomSeed() changes the random sequence."""
        # Seed with value 12345
        lib.SCOTCH_randomSeed(12345)
        seq1 = [lib.SCOTCH_randomVal(10000) for _ in range(100)]

        # Seed with different value
        lib.SCOTCH_randomSeed(67890)
        seq2 = [lib.SCOTCH_randomVal(10000) for _ in range(100)]

        # Sequences should be different
        assert seq1 != seq2, "Different seeds produced same sequence"

        # Re-seed with 12345 and verify we get seq1 again
        lib.SCOTCH_randomSeed(12345)
        seq3 = [lib.SCOTCH_randomVal(10000) for _ in range(100)]

        assert seq1 == seq3, "Same seed did not produce same sequence"

    def test_random_val_range(self):
        """Test SCOTCH_randomVal() respects various upper bounds."""
        # Test various upper bounds
        for upper_bound in [1, 10, 100, 1000, 10000]:
            for _ in range(50):
                val = lib.SCOTCH_randomVal(upper_bound)
                assert 0 <= val < upper_bound, \
                    f"randomVal({upper_bound}) returned {val}, expected [0, {upper_bound})"

    def test_random_val_zero_bound(self):
        """Test SCOTCH_randomVal(0) raises ValueError instead of crashing.

        Previously this would cause a floating-point exception (divide by zero)
        in Scotch. We now validate on the Python side to prevent the crash.
        """
        with pytest.raises(ValueError, match="randmax > 0"):
            lib.SCOTCH_randomVal(0)

        # Also test negative values
        with pytest.raises(ValueError, match="randmax > 0"):
            lib.SCOTCH_randomVal(-1)

    def test_random_val_one_bound(self):
        """Test SCOTCH_randomVal(1) returns only 0."""
        # With bound=1, only valid value is 0
        for _ in range(20):
            val = lib.SCOTCH_randomVal(1)
            assert val == 0, f"randomVal(1) returned {val}, expected 0"

    def test_random_distribution_uniformity(self):
        """Test that random values are reasonably uniform."""
        lib.SCOTCH_randomReset()

        # Generate many values in range [0, 10)
        bucket_count = 10
        samples = 1000
        buckets = [0] * bucket_count

        for _ in range(samples):
            val = lib.SCOTCH_randomVal(bucket_count)
            buckets[val] += 1

        # Each bucket should have roughly samples/bucket_count values
        expected = samples / bucket_count

        # Allow 30% deviation from expected (simple uniformity check)
        for i, count in enumerate(buckets):
            assert count > expected * 0.7, \
                f"Bucket {i} has too few values: {count} (expected ~{expected})"
            assert count < expected * 1.3, \
                f"Bucket {i} has too many values: {count} (expected ~{expected})"

    def test_random_large_bounds(self):
        """Test random generation with large upper bounds."""
        lib.SCOTCH_randomReset()

        # Test with large bounds
        large_bounds = [100000, 1000000, 10000000]

        for bound in large_bounds:
            values = [lib.SCOTCH_randomVal(bound) for _ in range(100)]

            # All values should be in range
            assert all(0 <= v < bound for v in values), \
                f"Some values out of range [0, {bound})"

            # Should have good diversity
            unique = len(set(values))
            assert unique > 80, \
                f"Too few unique values ({unique}/100) for bound {bound}"
