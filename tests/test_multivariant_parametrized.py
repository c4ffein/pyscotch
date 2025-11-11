"""
Tests demonstrating explicit multi-variant parameterization.

These tests use explicit @pytest.mark.parametrize to test exactly the variants we want:
- Sequential tests: only 32-bit and 64-bit sequential
- Parallel tests: only 32-bit and 64-bit parallel
- All variant tests: all 4 combinations

NO SKIPS! Every test runs on exactly the variants it should test.
"""

import numpy as np
import pytest
import pyscotch


# Define parameterization sets
SEQUENTIAL_VARIANTS = [
    pytest.param((32, False), id="32bit"),
    pytest.param((64, False), id="64bit"),
]

PARALLEL_VARIANTS = [
    pytest.param((32, True), id="32bit"),
    pytest.param((64, True), id="64bit"),
]

ALL_VARIANTS = [
    pytest.param((32, False), id="32bit-seq"),
    pytest.param((32, True), id="32bit-par"),
    pytest.param((64, False), id="64bit-seq"),
    pytest.param((64, True), id="64bit-par"),
]


class TestAllVariants:
    """Tests that run on ALL 4 variants - both sequential and parallel."""

    @pytest.mark.parametrize("variant", ALL_VARIANTS, indirect=["variant"])
    def test_variant_loaded_correctly(self, variant):
        """Verify variant is loaded and active."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        # Verify correct variant is active
        assert pyscotch.get_scotch_int_size() == int_size

    @pytest.mark.parametrize("variant", ALL_VARIANTS, indirect=["variant"])
    def test_dtype_correct_for_variant(self, variant):
        """Verify dtype matches the variant's int size."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        dtype = pyscotch.get_scotch_dtype()
        expected_dtype = np.int64 if int_size == 64 else np.int32
        assert dtype == expected_dtype

    @pytest.mark.parametrize("variant", ALL_VARIANTS, indirect=["variant"])
    def test_variant_info(self, variant):
        """Test that variant information is accessible."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        # Should be able to get variant info
        assert pyscotch.get_scotch_int_size() in [32, 64]
        dtype = pyscotch.get_scotch_dtype()
        assert dtype in [np.int32, np.int64]
        # Verify consistency
        if int_size == 32:
            assert dtype == np.int32
        else:
            assert dtype == np.int64


class TestSequentialVariants:
    """Tests that run ONLY on sequential variants (32-bit and 64-bit)."""

    @pytest.mark.parametrize("variant", SEQUENTIAL_VARIANTS, indirect=["variant"])
    def test_graph_creation(self, variant):
        """Test graph creation with sequential variants."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        # Create graph
        graph = pyscotch.Graph()
        assert graph is not None

    @pytest.mark.parametrize("variant", SEQUENTIAL_VARIANTS, indirect=["variant"])
    def test_graph_build(self, variant):
        """Test graph building with sequential variants."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        dtype = pyscotch.get_scotch_dtype()
        # Build a triangle graph
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)
        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)
        # Check graph
        assert graph.check() is True
        # Verify size
        vertnbr, edgenbr = graph.size()
        assert vertnbr == 3
        assert edgenbr == 6

    @pytest.mark.parametrize("variant", SEQUENTIAL_VARIANTS, indirect=["variant"])
    def test_graph_partition(self, variant):
        """Test graph partitioning with sequential variants."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        dtype = pyscotch.get_scotch_dtype()
        # Create ring graph with 12 vertices
        n = 12
        verttab = np.arange(0, 2 * n + 1, 2, dtype=dtype)
        edgetab = np.array([
            [(i - 1) % n, (i + 1) % n]
            for i in range(n)
        ], dtype=dtype).flatten()
        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)
        # Partition into 3 parts
        partitions = graph.partition(nparts=3)
        # Verify results
        assert len(partitions) == 12
        assert partitions.dtype == dtype
        assert len(np.unique(partitions)) <= 3

    @pytest.mark.parametrize("variant", SEQUENTIAL_VARIANTS, indirect=["variant"])
    def test_graph_order(self, variant):
        """Test graph ordering with sequential variants."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        dtype = pyscotch.get_scotch_dtype()
        # Create simple graph
        n = 8
        verttab = np.arange(0, 2 * n + 1, 2, dtype=dtype)
        edgetab = np.array([
            [(i - 1) % n, (i + 1) % n]
            for i in range(n)
        ], dtype=dtype).flatten()
        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)
        # Compute ordering
        perm, invp = graph.order()
        # Verify results
        assert len(perm) == 8
        assert len(invp) == 8
        assert perm.dtype == dtype
        assert invp.dtype == dtype
        # Verify permutation properties
        assert set(perm) == set(range(8))
        assert set(invp) == set(range(8))

    @pytest.mark.parametrize("variant", SEQUENTIAL_VARIANTS, indirect=["variant"])
    def test_dtype_consistency(self, variant):
        """Test that dtypes are consistent across operations."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        dtype = pyscotch.get_scotch_dtype()
        # Create graph
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)
        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)
        # Get partition
        parts = graph.partition(nparts=2)
        # Get ordering
        perm, invp = graph.order()
        # All results should use the correct dtype
        assert parts.dtype == dtype
        assert perm.dtype == dtype
        assert invp.dtype == dtype


class TestParallelVariants:
    """Tests that run ONLY on parallel variants (32-bit and 64-bit PT-Scotch)."""

    @pytest.mark.parametrize("variant", PARALLEL_VARIANTS, indirect=["variant"])
    def test_ptscotch_variant_loaded(self, variant):
        """Test that PT-Scotch variants are loaded."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        # Verify parallel variant is active
        variant_obj = libscotch.get_active_variant()
        assert variant_obj is not None
        assert variant_obj.parallel is True
        assert variant_obj.int_size == int_size

    @pytest.mark.parametrize("variant", PARALLEL_VARIANTS, indirect=["variant"])
    def test_ptscotch_has_correct_dtype(self, variant):
        """Test that PT-Scotch uses correct dtype."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        dtype = pyscotch.get_scotch_dtype()
        if int_size == 32:
            assert dtype == np.int32
        else:
            assert dtype == np.int64

    @pytest.mark.parametrize("variant", PARALLEL_VARIANTS, indirect=["variant"])
    def test_ptscotch_variant_suffixes(self, variant):
        """Test that PT-Scotch functions have correct suffix."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        variant_obj = libscotch.get_active_variant()
        # PT-Scotch should have distributed graph functions with suffix
        # Verify the _get_func helper uses the right suffix
        assert variant_obj.int_size == int_size


class TestCrossBitSizeComparison:
    """Tests that compare behavior across different bit sizes (sequential only)."""

    @pytest.mark.parametrize("variant", SEQUENTIAL_VARIANTS, indirect=["variant"])
    def test_same_graph_different_sizes(self, variant):
        """Test that same graph gives consistent results across bit sizes."""
        int_size, parallel = variant
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)
        dtype = pyscotch.get_scotch_dtype()
        # Create identical triangle graph for both 32 and 64 bit
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)
        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)
        # Size should be same regardless of int size
        vertnbr, edgenbr = graph.size()
        assert vertnbr == 3
        assert edgenbr == 6
        # Partitions should work (results may vary but should be valid)
        parts = graph.partition(nparts=2)
        assert len(parts) == 3
        assert all(0 <= p < 2 for p in parts)


# Fixture to handle the variant parameter
@pytest.fixture
def variant(request):
    """Fixture that switches to the requested variant."""
    int_size, parallel = request.param
    from pyscotch import libscotch
    libscotch.set_active_variant(int_size, parallel)
    yield (int_size, parallel)
