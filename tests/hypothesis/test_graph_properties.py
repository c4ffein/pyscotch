"""
Property-based tests for pyscotch Graph operations using Hypothesis.

These tests verify fundamental invariants that must hold for ANY valid graph:
- Ordering produces valid bijective permutations
- Partitioning assigns all vertices to valid partitions
- Graph coloring produces valid colorings (no adjacent vertices share colors)
"""

import pytest
import numpy as np
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from pyscotch import Graph
from pyscotch import libscotch as lib


# =============================================================================
# Strategies for generating valid graphs
# =============================================================================

@st.composite
def valid_edges(draw, num_vertices):
    """
    Generate a list of valid edges for a graph with num_vertices vertices.

    Ensures:
    - No self-loops (u != v)
    - No duplicate edges
    - All vertex indices in valid range [0, num_vertices)
    """
    if num_vertices < 2:
        return []

    # Generate unique edges
    max_edges = min(num_vertices * (num_vertices - 1) // 2, 50)  # Cap for performance
    num_edges = draw(st.integers(min_value=1, max_value=max(1, max_edges)))

    edges = set()
    for _ in range(num_edges * 2):  # Try more times to get unique edges
        if len(edges) >= num_edges:
            break
        u = draw(st.integers(min_value=0, max_value=num_vertices - 1))
        v = draw(st.integers(min_value=0, max_value=num_vertices - 1))
        if u != v:
            # Store as sorted tuple to avoid (u,v) and (v,u) duplicates
            edges.add((min(u, v), max(u, v)))

    return list(edges)


@st.composite
def simple_graph(draw, min_vertices=2, max_vertices=20):
    """
    Generate a valid simple graph (no self-loops, no multi-edges).

    Returns:
        tuple: (num_vertices, edges) where edges is a list of (u, v) tuples
    """
    num_vertices = draw(st.integers(min_value=min_vertices, max_value=max_vertices))
    edges = draw(valid_edges(num_vertices))
    assume(len(edges) > 0)  # Need at least one edge for meaningful tests
    return (num_vertices, edges)


@st.composite
def connected_graph(draw, min_vertices=2, max_vertices=15):
    """
    Generate a connected graph by first creating a spanning tree, then adding random edges.

    This ensures the graph is connected, which is important for some operations.
    """
    num_vertices = draw(st.integers(min_value=min_vertices, max_value=max_vertices))

    # Create spanning tree (ensures connectivity)
    edges = set()
    if num_vertices >= 2:
        # Build a random spanning tree
        in_tree = {0}
        not_in_tree = set(range(1, num_vertices))

        while not_in_tree:
            # Pick a random vertex not in tree
            v = draw(st.sampled_from(sorted(not_in_tree)))
            not_in_tree.remove(v)

            # Connect to random vertex in tree
            u = draw(st.sampled_from(sorted(in_tree)))
            in_tree.add(v)
            edges.add((min(u, v), max(u, v)))

    # Optionally add more edges
    max_extra = min(num_vertices, 10)
    num_extra = draw(st.integers(min_value=0, max_value=max_extra))

    for _ in range(num_extra * 2):
        if len(edges) >= num_vertices - 1 + num_extra:
            break
        u = draw(st.integers(min_value=0, max_value=num_vertices - 1))
        v = draw(st.integers(min_value=0, max_value=num_vertices - 1))
        if u != v:
            edges.add((min(u, v), max(u, v)))

    return (num_vertices, list(edges))


# =============================================================================
# Property Tests
# =============================================================================

class TestOrderingProperties:
    """Property tests for Graph.order() - the ordering must be a valid bijection."""

    @given(graph_data=connected_graph(min_vertices=2, max_vertices=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_ordering_permutation_inverse_identity(self, graph_data):
        """
        Property: inverse[permutation[i]] == i for all vertices.

        The ordering returns (permutation, inverse) which must satisfy:
        - permutation: old index -> new index
        - inverse: new index -> old index
        - They are inverses of each other
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        permutation, inverse = graph.order()

        # Verify lengths
        assert len(permutation) == num_vertices
        assert len(inverse) == num_vertices

        # Property: inverse[permutation[i]] == i
        for i in range(num_vertices):
            assert inverse[permutation[i]] == i, \
                f"inverse[permutation[{i}]] = {inverse[permutation[i]]} != {i}"

    @given(graph_data=connected_graph(min_vertices=2, max_vertices=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_ordering_inverse_permutation_identity(self, graph_data):
        """
        Property: permutation[inverse[i]] == i for all vertices.

        The inverse property in the other direction.
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        permutation, inverse = graph.order()

        # Property: permutation[inverse[i]] == i
        for i in range(num_vertices):
            assert permutation[inverse[i]] == i, \
                f"permutation[inverse[{i}]] = {permutation[inverse[i]]} != {i}"

    @given(graph_data=connected_graph(min_vertices=2, max_vertices=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_ordering_is_bijection(self, graph_data):
        """
        Property: permutation and inverse are both valid permutations.

        Each must contain all values 0..n-1 exactly once.
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        permutation, inverse = graph.order()

        # Both should be permutations of [0, n-1]
        expected = set(range(num_vertices))

        assert set(permutation) == expected, \
            f"permutation is not a valid permutation: {sorted(set(permutation))} != {sorted(expected)}"
        assert set(inverse) == expected, \
            f"inverse is not a valid permutation: {sorted(set(inverse))} != {sorted(expected)}"


class TestPartitionProperties:
    """Property tests for Graph.partition() - partition validity invariants."""

    @given(
        graph_data=simple_graph(min_vertices=3, max_vertices=20),
        nparts=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_partition_covers_all_vertices(self, graph_data, nparts):
        """
        Property: Partition array has one entry per vertex.
        """
        num_vertices, edges = graph_data
        assume(nparts <= num_vertices)  # Can't have more partitions than vertices

        graph = Graph.from_edges(edges, num_vertices=num_vertices)
        partition = graph.partition(nparts=nparts)

        assert len(partition) == num_vertices, \
            f"Partition length {len(partition)} != num_vertices {num_vertices}"

    @given(
        graph_data=simple_graph(min_vertices=3, max_vertices=20),
        nparts=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_partition_values_in_valid_range(self, graph_data, nparts):
        """
        Property: All partition values are in [0, nparts).
        """
        num_vertices, edges = graph_data
        assume(nparts <= num_vertices)

        graph = Graph.from_edges(edges, num_vertices=num_vertices)
        partition = graph.partition(nparts=nparts)

        assert partition.min() >= 0, \
            f"Partition contains negative value: {partition.min()}"
        assert partition.max() < nparts, \
            f"Partition value {partition.max()} >= nparts {nparts}"


class TestColoringProperties:
    """Property tests for Graph.color() - coloring validity invariants."""

    @pytest.mark.xfail(reason="Upstream Scotch bug with sparse graphs - see docs/QUESTIONS_FOR_SCOTCH_TEAM_2.md")
    @given(graph_data=simple_graph(min_vertices=2, max_vertices=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_coloring_no_adjacent_same_color(self, graph_data):
        """
        Property: No two adjacent vertices have the same color.

        This is the fundamental invariant of graph coloring.

        NOTE: This test is xfail due to an upstream Scotch bug where
        SCOTCH_graphColor returns invalid colorings for sparse graphs
        when vertex 0 is isolated and an edge connects to the last vertex.
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        coloring, num_colors = graph.color()

        # Verify the fundamental coloring property
        for u, v in edges:
            assert coloring[u] != coloring[v], \
                f"Adjacent vertices {u} and {v} have same color {coloring[u]}"

    @given(graph_data=simple_graph(min_vertices=2, max_vertices=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_coloring_values_consistent_with_count(self, graph_data):
        """
        Property: Color values are in [0, num_colors) and num_colors > 0.
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        coloring, num_colors = graph.color()

        # Must have at least one color
        assert num_colors > 0, "num_colors must be positive"

        # All color values must be valid
        assert coloring.min() >= 0, \
            f"Coloring contains negative value: {coloring.min()}"
        assert coloring.max() < num_colors, \
            f"Color value {coloring.max()} >= num_colors {num_colors}"

    @given(graph_data=simple_graph(min_vertices=2, max_vertices=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_coloring_length_matches_vertices(self, graph_data):
        """
        Property: Coloring array has one entry per vertex.
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        coloring, _ = graph.color()

        assert len(coloring) == num_vertices, \
            f"Coloring length {len(coloring)} != num_vertices {num_vertices}"


class TestGraphCheckProperty:
    """Property tests for Graph.check() - built graphs should be valid."""

    @given(graph_data=simple_graph(min_vertices=2, max_vertices=30))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_from_edges_produces_valid_graph(self, graph_data):
        """
        Property: Any graph built from valid edges passes check().
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        assert graph.check(), \
            f"Graph.check() failed for graph with {num_vertices} vertices and {len(edges)} edges"

    @given(graph_data=connected_graph(min_vertices=2, max_vertices=30))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_connected_graph_is_valid(self, graph_data):
        """
        Property: Connected graphs built from spanning tree + edges pass check().
        """
        num_vertices, edges = graph_data
        graph = Graph.from_edges(edges, num_vertices=num_vertices)

        assert graph.check(), \
            f"Connected graph check() failed for {num_vertices} vertices"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
