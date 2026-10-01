"""
Unit tests for Graph class.
"""

import pytest
import numpy as np
from pathlib import Path
from pyscotch import Graph, Strategy, Mapping


class TestGraph:
    """Test Graph functionality."""

    def test_graph_creation(self):
        """Test creating an empty graph."""
        graph = Graph()
        assert graph is not None

    def test_graph_from_edges(self):
        """Test creating a graph from edge list."""
        edges = [(0, 1), (1, 2), (2, 0)]
        graph = Graph.from_edges(edges, num_vertices=3)
        assert graph is not None

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 3
        assert edgenbr > 0

    def test_graph_build(self):
        """Test building a graph from arrays."""
        # Simple triangle graph
        verttab = np.array([0, 2, 4, 6], dtype=np.int64)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=np.int64)

        graph = Graph()
        graph.build(verttab, edgetab, baseval=0)

        vertnbr, edgenbr = graph.size()
        assert vertnbr == 3
        assert edgenbr == 6

    def test_graph_check(self):
        """Test graph consistency checking."""
        edges = [(0, 1), (1, 2), (2, 0)]
        graph = Graph.from_edges(edges, num_vertices=3)
        assert graph.check() is True

    def test_graph_partition(self):
        """Test graph partitioning."""
        # Create a larger graph
        edges = []
        for i in range(10):
            edges.append((i, (i + 1) % 10))

        graph = Graph.from_edges(edges, num_vertices=10)
        partitions = graph.partition(nparts=2)

        assert len(partitions) == 10
        assert partitions.min() >= 0
        assert partitions.max() < 2

    def test_graph_partition_with_strategy(self):
        """Test partitioning with custom strategy."""
        edges = [(i, (i + 1) % 10) for i in range(10)]
        graph = Graph.from_edges(edges, num_vertices=10)

        strategy = Strategy()  # a fresh Strategy is Scotch's default

        partitions = graph.partition(nparts=3, strategy=strategy)
        assert len(partitions) == 10
        assert partitions.max() < 3

    def test_graph_order(self):
        """Test graph ordering."""
        edges = [(i, (i + 1) % 8) for i in range(8)]
        graph = Graph.from_edges(edges, num_vertices=8)

        permutation, inverse = graph.order()

        assert len(permutation) == 8
        assert len(inverse) == 8

        # Check that permutation and inverse are valid
        for i in range(8):
            assert inverse[permutation[i]] == i

    def test_mapping_class(self):
        """Test Mapping class functionality."""
        partitions = np.array([0, 0, 1, 1, 2, 2], dtype=np.int64)
        mapping = Mapping(partitions)

        assert mapping.num_partitions() == 3
        assert len(mapping) == 6

        sizes = mapping.get_partition_sizes()
        assert len(sizes) == 3
        assert all(sizes == 2)

        # Test balance
        balance = mapping.balance()
        assert balance == 1.0  # Perfect balance

    def test_mapping_unbalanced(self):
        """Test mapping with unbalanced partitions."""
        partitions = np.array([0, 0, 0, 1, 1, 2], dtype=np.int64)
        mapping = Mapping(partitions)

        balance = mapping.balance()
        assert balance > 1.0  # Unbalanced

        sizes = mapping.get_partition_sizes()
        assert sizes[0] == 3
        assert sizes[1] == 2
        assert sizes[2] == 1


class TestStrategy:
    """Test Strategy functionality."""

    def test_strategy_creation(self):
        """Test creating a strategy."""
        strategy = Strategy()
        assert strategy is not None

    def test_strategy_methods(self):
        """Test strategy configuration methods."""
        strategy = Strategy()

        strategy.reset()
        strategy.set_recursive_bisection()

        strategy.reset()


class TestFromEdgesInputs:
    """Graph.from_edges: weights, input validation, and accepted containers."""

    def test_edge_weights_one_per_edge_apply_to_both_arcs(self):
        """edge_weights has one entry per input edge; Scotch stores one load
        per arc, so each weight must land on both directions of its edge."""
        graph = Graph.from_edges([(0, 1), (1, 2), (2, 0)], edge_weights=[1, 2, 3])
        assert graph.check() is True
        stats = graph.stat()
        assert (stats["edlomin"], stats["edlomax"], stats["edlosum"]) == (1, 3, 12)
        indptr, indices, edlotab = graph._csr_arrays()
        load = {}
        for u in range(3):
            for k in range(int(indptr[u]), int(indptr[u + 1])):
                load[(u, int(indices[k]))] = int(edlotab[k])
        assert load == {
            (0, 1): 1, (1, 0): 1,
            (1, 2): 2, (2, 1): 2,
            (2, 0): 3, (0, 2): 3,
        }

    def test_edge_weights_length_must_match_edges(self):
        with pytest.raises(ValueError, match="edge_weights length"):
            Graph.from_edges([(0, 1), (1, 2)], edge_weights=[1, 2, 3])

    def test_edge_weights_must_be_strictly_positive_integers(self):
        with pytest.raises(ValueError, match="strictly positive"):
            Graph.from_edges([(0, 1), (1, 2)], edge_weights=[1, 0])
        with pytest.raises(ValueError, match="integers"):
            Graph.from_edges([(0, 1), (1, 2)], edge_weights=[1, 2.5])

    def test_vertex_weights_accept_numpy_arrays(self):
        weights = np.array([1, 2, 3])
        graph = Graph.from_edges([(0, 1), (1, 2)], vertex_weights=weights)
        assert graph.check() is True
        assert graph.stat()["velosum"] == 6

    def test_self_loop_rejected(self):
        """Scotch graphs cannot contain self-loops (from_scipy_sparse and
        from_networkx already refuse them); from_edges must not build a
        graph that fails its own check()."""
        with pytest.raises(ValueError, match="self-loop"):
            Graph.from_edges([(0, 1), (1, 1), (1, 2)])

    def test_duplicate_edge_rejected_in_either_direction(self):
        with pytest.raises(ValueError, match="duplicate"):
            Graph.from_edges([(0, 1), (0, 1), (1, 2)])
        with pytest.raises(ValueError, match="duplicate"):
            Graph.from_edges([(0, 1), (1, 0), (1, 2)])

    def test_negative_vertex_rejected(self):
        with pytest.raises(ValueError, match="negative"):
            Graph.from_edges([(0, 1), (-1, 2)], num_vertices=3)

    def test_accepts_any_iterable_of_pairs(self):
        """Hypothesis tests pass sets; generators must not be silently consumed
        twice."""
        graph = Graph.from_edges({(0, 1), (1, 2)})
        assert graph.size() == (3, 4)
        graph = Graph.from_edges(((u, u + 1) for u in range(3)))
        assert graph.size() == (4, 6)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
