"""
Unit tests ported from Scotch C test suite.

These tests are based on the tests in external/scotch/src/check/
to ensure compatibility with the original Scotch library.

Single-Variant Design:
Tests run with ONE Scotch variant, configured via environment variables:
- PYSCOTCH_INT_SIZE: 32 or 64 (default: 32)
- PYSCOTCH_PARALLEL: 0 or 1 (default: 0)

To test all variants, run the test suite multiple times with different configurations.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import os
from pyscotch import Graph, Strategy, Architecture, Mapping, Ordering
from pyscotch import libscotch as lib


class TestArchitecture:
    """Tests based on test_scotch_arch.c"""

    def test_arch_cmplt_creation(self):
        """Test creating a complete graph architecture."""
        arch = Architecture()
        arch.complete(8)
        # Architecture should be created successfully
        assert arch is not None

    def test_arch_cmplt_sizes(self):
        """Test different complete architecture sizes."""
        for size in [1, 2, 4, 8, 16, 32]:
            arch = Architecture()
            arch.complete(size)
            assert arch is not None


class TestGraphBasic:
    """Basic graph tests based on Scotch C tests."""

    def test_graph_init_exit(self):
        """Test graph initialization and cleanup."""
        graph = Graph()
        assert graph is not None
        # Cleanup happens automatically via __del__

    def test_graph_size_empty(self):
        """Test getting size of an uninitialized graph."""
        # Empty graph should have 0 vertices and 0 edges
        graph = Graph()
        vertnbr, edgenbr = graph.size()
        assert vertnbr == 0
        assert edgenbr == 0

    def test_simple_triangle_csr(self):
        """Test building a simple triangle graph using CSR format.

        Graph structure:
          0 -- 1
          |    |
          2 ---+
        """
        # CSR format for undirected triangle
        # Vertex 0: neighbors [1, 2]
        # Vertex 1: neighbors [0, 2]
        # Vertex 2: neighbors [0, 1]
        verttab = np.array([0, 2, 4, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 3
        assert edgenbr == 6

    def test_simple_path_csr(self):
        """Test building a simple path graph using CSR format.

        Graph structure: 0 - 1 - 2 - 3
        """
        # Vertex 0: neighbors [1]
        # Vertex 1: neighbors [0, 2]
        # Vertex 2: neighbors [1, 3]
        # Vertex 3: neighbors [2]
        verttab = np.array([0, 1, 3, 5, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 0, 2, 1, 3, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 4
        assert edgenbr == 6

    def test_simple_star_csr(self):
        """Test building a star graph using CSR format.

        Graph structure:
            1
            |
        2 - 0 - 3
            |
            4
        """
        # Vertex 0: neighbors [1, 2, 3, 4] (center)
        # Vertex 1: neighbors [0]
        # Vertex 2: neighbors [0]
        # Vertex 3: neighbors [0]
        # Vertex 4: neighbors [0]
        verttab = np.array([0, 4, 5, 6, 7, 8], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 3, 4, 0, 0, 0, 0], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 5
        assert edgenbr == 8


    def test_simple_grid_2x2_csr(self):
        """Test building a 2x2 grid graph using CSR format.

        Graph structure:
        0 -- 1
        |    |
        2 -- 3
        """
        # Vertex 0: neighbors [1, 2]
        # Vertex 1: neighbors [0, 3]
        # Vertex 2: neighbors [0, 3]
        # Vertex 3: neighbors [1, 2]
        verttab = np.array([0, 2, 4, 6, 8], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 3, 0, 3, 1, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 4
        assert edgenbr == 8

    def test_graph_check_triangle(self):
        """Test graph consistency check on triangle graph."""
        verttab = np.array([0, 2, 4, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        # Check should pass for valid graph
        assert graph.check() is True

    def test_graph_check_path(self):
        """Test graph consistency check on path graph."""
        verttab = np.array([0, 1, 3, 5, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 0, 2, 1, 3, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        assert graph.check() is True


class TestGraphPartitioning:
    """Graph partitioning tests based on Scotch C tests."""

    def test_partition_triangle_2parts(self):
        """Test partitioning triangle graph into 2 parts."""
        verttab = np.array([0, 2, 4, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        partitions = graph.partition(nparts=2)

        assert len(partitions) == 3
        assert partitions.min() >= 0
        assert partitions.max() <= 1

    def test_partition_path_2parts(self):
        """Test partitioning path graph into 2 parts."""
        verttab = np.array([0, 1, 3, 5, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 0, 2, 1, 3, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        partitions = graph.partition(nparts=2)

        assert len(partitions) == 4
        assert partitions.min() >= 0
        assert partitions.max() <= 1

    def test_partition_grid_2x2_2parts(self):
        """Test partitioning 2x2 grid into 2 parts."""
        verttab = np.array([0, 2, 4, 6, 8], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 3, 0, 3, 1, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        partitions = graph.partition(nparts=2)

        assert len(partitions) == 4
        assert partitions.min() >= 0
        assert partitions.max() <= 1
        # Both partitions should be used
        assert len(np.unique(partitions)) == 2

    def test_partition_grid_2x2_4parts(self):
        """Test partitioning 2x2 grid into 4 parts."""
        verttab = np.array([0, 2, 4, 6, 8], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 3, 0, 3, 1, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        partitions = graph.partition(nparts=4)

        assert len(partitions) == 4
        assert partitions.min() >= 0
        assert partitions.max() <= 3

    def test_partition_larger_path(self):
        """Test partitioning larger path graph."""
        # Create path: 0 - 1 - 2 - 3 - 4 - 5 - 6 - 7
        n = 8
        verttab = np.zeros(n + 1, dtype=lib.get_dtype())
        edges = []

        # Build edge list for path
        for i in range(n):
            if i > 0:
                edges.append(i - 1)
            if i < n - 1:
                edges.append(i + 1)
            verttab[i + 1] = len(edges)

        edgetab = np.array(edges, dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        partitions = graph.partition(nparts=2)

        assert len(partitions) == n
        assert partitions.min() >= 0
        assert partitions.max() <= 1


class TestGraphOrdering:
    """Graph ordering tests based on Scotch C tests."""

    def test_order_triangle(self):
        """Test ordering triangle graph."""
        verttab = np.array([0, 2, 4, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        permutation, inverse = graph.order()

        assert len(permutation) == 3
        assert len(inverse) == 3

        # Check that permutation and inverse are valid
        for i in range(3):
            assert inverse[permutation[i]] == i

    def test_order_path(self):
        """Test ordering path graph."""
        verttab = np.array([0, 1, 3, 5, 6], dtype=lib.get_dtype())
        edgetab = np.array([1, 0, 2, 1, 3, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        permutation, inverse = graph.order()

        assert len(permutation) == 4
        assert len(inverse) == 4

        # Verify permutation properties
        for i in range(4):
            assert inverse[permutation[i]] == i

    def test_order_grid_2x2(self):
        """Test ordering 2x2 grid graph."""
        verttab = np.array([0, 2, 4, 6, 8], dtype=lib.get_dtype())
        edgetab = np.array([1, 2, 0, 3, 0, 3, 1, 2], dtype=lib.get_dtype())

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        permutation, inverse = graph.order()

        assert len(permutation) == 4
        assert len(inverse) == 4

        # Verify bijection
        for i in range(4):
            assert inverse[permutation[i]] == i


class TestStrategy:
    """Strategy tests based on Scotch C tests."""

    def test_strategy_init_exit(self):
        """Test strategy initialization and cleanup."""
        strategy = Strategy()
        assert strategy is not None

    def test_strategy_mapping_default(self):
        """Test setting default mapping strategy."""
        strategy = Strategy()
        strategy.set_mapping_default()
        assert strategy.strategy_string == ""

    def test_strategy_ordering_default(self):
        """Test setting default ordering strategy."""
        strategy = Strategy()
        strategy.set_ordering_default()
        assert strategy.strategy_string == ""

    def test_strategy_recursive_bisection(self):
        """Test setting recursive bisection strategy."""
        strategy = Strategy()
        strategy.set_recursive_bisection()
        assert strategy.strategy_string == "r"

    def test_strategy_multilevel(self):
        """Test setting multilevel strategy."""
        strategy = Strategy()
        strategy.set_multilevel()
        assert strategy.strategy_string == "m"


class TestCompatLibrary:
    """Test that libpyscotch_compat.so is built and loadable."""

    @pytest.fixture
    def int_size(self, scotch_int_size):
        """Get the current int size from conftest fixture."""
        return scotch_int_size

    def test_compat_library_exists(self, int_size):
        """Verify compat library file exists for this variant."""
        lib_size = "lib64" if int_size == 64 else "lib32"
        compat_path = os.path.join("scotch-builds", lib_size, "libpyscotch_compat.so")
        assert os.path.exists(compat_path), (
            f"Compatibility library not found: {compat_path}\n"
            "Please rebuild with 'make build-all'"
        )

    def test_compat_library_loads(self, int_size):
        """Verify compat library can be loaded via c_fopen."""
        from pyscotch.graph import c_fopen

        # Create a test file and try to open it with c_fopen
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('test')
            test_file = f.name

        try:
            with c_fopen(test_file, 'r') as fp:
                assert fp is not None, "c_fopen returned NULL"
                # FILE* pointer should be a valid memory address
                assert isinstance(fp, int) and fp > 0, f"Invalid FILE* pointer: {fp}"
        finally:
            os.unlink(test_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
