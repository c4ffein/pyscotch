"""
Tests for verifying PyScotch works correctly with both 32-bit and 64-bit Scotch builds.

Run these tests with different PYSCOTCH_INT_SIZE environment variables:
    pytest tests/test_int_sizes.py                    # Tests with 32-bit
    PYSCOTCH_INT_SIZE=64 pytest tests/test_int_sizes.py  # Tests with 64-bit

Or test both:
    pytest tests/test_int_sizes.py && PYSCOTCH_INT_SIZE=64 pytest tests/test_int_sizes.py
"""

import pytest
import numpy as np
import pyscotch


class TestIntSizeConfiguration:
    """Tests that verify the correct Scotch variant is loaded."""

    def test_correct_int_size_loaded(self, scotch_int_size):
        """Verify the correct Scotch variant is loaded."""
        assert pyscotch.get_scotch_int_size() == scotch_int_size

    def test_correct_dtype(self, scotch_int_size):
        """Verify the correct numpy dtype is used."""
        dtype = pyscotch.get_scotch_dtype()
        if scotch_int_size == 32:
            assert dtype == np.int32
        else:
            assert dtype == np.int64


class TestGraphOperations:
    """Test graph operations work correctly with current int size."""

    def test_graph_creation(self, scotch_int_size):
        """Test graph creation with parameterized int size."""
        graph = pyscotch.Graph()
        assert graph is not None

    def test_graph_build_with_correct_dtype(self, scotch_int_size):
        """Test building a graph uses correct dtype."""
        dtype = pyscotch.get_scotch_dtype()

        # Triangle graph
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)

        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 3
        assert edgenbr == 6

    def test_graph_check(self, scotch_int_size):
        """Test graph validation works with both int sizes."""
        dtype = pyscotch.get_scotch_dtype()

        # Simple valid graph
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)

        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)

        # Check should pass
        assert graph.check() is True

    def test_graph_partition(self, scotch_int_size):
        """Test graph partitioning with both int sizes."""
        dtype = pyscotch.get_scotch_dtype()

        # Create a ring graph with 12 vertices
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

        assert len(partitions) == n
        assert partitions.min() >= 0
        assert partitions.max() < 3
        assert partitions.dtype == dtype

    def test_graph_order(self, scotch_int_size):
        """Test graph ordering with both int sizes."""
        dtype = pyscotch.get_scotch_dtype()

        # Create a simple graph
        n = 8
        verttab = np.arange(0, 2 * n + 1, 2, dtype=dtype)
        edgetab = np.array([
            [(i - 1) % n, (i + 1) % n]
            for i in range(n)
        ], dtype=dtype).flatten()

        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)

        # Compute ordering
        perm, inv = graph.order()

        assert len(perm) == n
        assert len(inv) == n
        assert perm.dtype == dtype
        assert inv.dtype == dtype

        # Verify permutation/inverse relationship
        for i in range(n):
            assert inv[perm[i]] == i

    def test_from_edges_helper(self, scotch_int_size):
        """Test from_edges helper method with both int sizes."""
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        graph = pyscotch.Graph.from_edges(edges, num_vertices=4)

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 4
        assert edgenbr == 8  # Undirected, so each edge counted twice

    def test_large_graph(self, scotch_int_size):
        """Test with a larger graph to stress test the int size."""
        dtype = pyscotch.get_scotch_dtype()

        # Create a grid graph 10x10
        n = 100
        edges = []
        for i in range(10):
            for j in range(10):
                v = i * 10 + j
                # Connect to neighbors
                if j < 9:
                    edges.append((v, v + 1))
                if i < 9:
                    edges.append((v, v + 10))

        graph = pyscotch.Graph.from_edges(edges, num_vertices=n)
        vertnbr, edgenbr = graph.size()

        assert vertnbr == 100

        # Partition the graph
        partitions = graph.partition(nparts=4)
        assert len(partitions) == n
        assert partitions.dtype == dtype


class TestSpecificIntSizes:
    """Tests that verify variant-specific behavior using explicit parameterization."""

    # All 4 variants for switching tests
    @pytest.mark.parametrize("int_size,parallel", [
        pytest.param(32, False, id="32bit-seq"),
        pytest.param(32, True, id="32bit-par"),
        pytest.param(64, False, id="64bit-seq"),
        pytest.param(64, True, id="64bit-par"),
    ])
    def test_variant_switching(self, int_size, parallel):
        """Test that variant switching works correctly."""
        # Switch to this variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel)

        # Verify the active variant matches what was requested
        assert pyscotch.get_scotch_int_size() == int_size

        # Verify dtype matches
        dtype = pyscotch.get_scotch_dtype()
        if int_size == 32:
            assert dtype == np.int32
        else:
            assert dtype == np.int64

    # Only sequential variants for graph operations
    @pytest.mark.parametrize("int_size", [
        pytest.param(32, id="32bit"),
        pytest.param(64, id="64bit"),
    ])
    def test_variant_graph_operations(self, int_size):
        """Test that graph operations work with each sequential variant."""
        # Switch to sequential variant
        from pyscotch import libscotch
        libscotch.set_active_variant(int_size, parallel=False)

        dtype = pyscotch.get_scotch_dtype()

        # Create a simple graph with the correct dtype
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)

        graph = pyscotch.Graph()
        graph.build(verttab, edgetab, baseval=0)

        # Should work for both 32-bit and 64-bit
        assert graph.check() is True

        # Verify operations return correct dtype
        vertnbr, edgenbr = graph.size()
        parts = graph.partition(nparts=2)
        assert parts.dtype == dtype


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
