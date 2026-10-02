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

    @given(graph_data=simple_graph(min_vertices=2, max_vertices=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_coloring_no_adjacent_same_color(self, graph_data):
        """
        Property: No two adjacent vertices have the same color.

        This is the fundamental invariant of graph coloring.

        This test caught an upstream Scotch bug (see docs/COLORING_BUG_RESOLUTION.md),
        fixed in Scotch v7.0.11 (commit e0a90c7).
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


# =============================================================================
# Weighted graphs through from_edges
# =============================================================================

@st.composite
def weighted_graph(draw, min_vertices=2, max_vertices=20, min_vertex_weight=0):
    """A simple graph plus one load per vertex and one per edge.

    Edge loads are strictly positive (Scotch rejects zero edge loads); vertex
    loads may be zero unless min_vertex_weight says otherwise.
    """
    num_vertices, edges = draw(simple_graph(min_vertices, max_vertices))
    edge_weights = draw(st.lists(st.integers(1, 1000), min_size=len(edges), max_size=len(edges)))
    vertex_weights = draw(
        st.lists(st.integers(min_vertex_weight, 1000), min_size=num_vertices, max_size=num_vertices)
    )
    return num_vertices, edges, vertex_weights, edge_weights


def _arc_loads(graph):
    """{(u, v): load} for every arc of the graph, from Scotch's own arrays.

    A graph without an edge load array has unit loads (Scotch semantics;
    from_edges deliberately passes no array when every weight is 1).
    """
    indptr, indices, edlotab = graph._csr_arrays()
    loads = {}
    for u in range(len(indptr) - 1):
        for k in range(int(indptr[u]), int(indptr[u + 1])):
            loads[(u, int(indices[k]))] = 1 if edlotab is None else int(edlotab[k])
    return loads


class TestFromEdgesWeightProperties:
    """Property tests for Graph.from_edges with vertex_weights / edge_weights."""

    @given(data=weighted_graph())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_each_edge_weight_lands_on_both_arcs(self, data):
        """
        Property: edge_weights has one entry per input edge; Scotch stores one
        load per ARC, and both arcs of an edge carry exactly that edge's weight.
        """
        num_vertices, edges, vertex_weights, edge_weights = data
        graph = Graph.from_edges(
            edges, num_vertices=num_vertices, vertex_weights=vertex_weights, edge_weights=edge_weights
        )
        assert graph.check(), "weighted graph fails Scotch's own check()"

        loads = _arc_loads(graph)
        assert len(loads) == 2 * len(edges), "every edge must yield exactly two arcs"
        for (u, v), w in zip(edges, edge_weights):
            assert loads[(u, v)] == w, f"arc ({u},{v}) carries {loads[(u, v)]}, edge weight is {w}"
            assert loads[(v, u)] == w, f"arc ({v},{u}) carries {loads[(v, u)]}, edge weight is {w}"

        stats = graph.stat()
        assert stats["edlomin"] == min(edge_weights)
        assert stats["edlomax"] == max(edge_weights)
        if all(w == 1 for w in edge_weights):
            # No load array is passed for unit weights, and SCOTCH_graphStat
            # then reports edlosum = edgenbr / 2 (per EDGE), whereas with a
            # load array it sums per ARC (library_graph.c, SCOTCH_graphStat).
            # Pinned as-is; see QUESTIONS_FOR_SCOTCH_TEAM.md.
            assert stats["edlosum"] == len(edges)
        else:
            assert stats["edlosum"] == 2 * sum(edge_weights)

    @given(data=weighted_graph())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_vertex_weights_are_kept_verbatim(self, data):
        """
        Property: vertex loads (zero allowed) reach Scotch unchanged.
        """
        num_vertices, edges, vertex_weights, _ = data
        graph = Graph.from_edges(edges, num_vertices=num_vertices, vertex_weights=vertex_weights)
        assert graph.check()
        stats = graph.stat()
        assert stats["velosum"] == sum(vertex_weights)
        assert stats["velomin"] == min(vertex_weights)
        assert stats["velomax"] == max(vertex_weights)

    @given(data=weighted_graph())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_weights_do_not_change_the_structure(self, data):
        """
        Property: the weighted graph has the same adjacency as the unweighted one.
        """
        num_vertices, edges, vertex_weights, edge_weights = data
        plain = Graph.from_edges(edges, num_vertices=num_vertices)
        weighted = Graph.from_edges(
            edges, num_vertices=num_vertices, vertex_weights=vertex_weights, edge_weights=edge_weights
        )
        assert plain.size() == weighted.size()
        p_indptr, p_indices, p_loads = plain._csr_arrays()
        w_indptr, w_indices, w_loads = weighted._csr_arrays()
        assert p_loads is None
        # all-ones weights are unit loads: from_edges then passes no load array at all
        assert (w_loads is None) == all(w == 1 for w in edge_weights)
        assert list(p_indptr) == list(w_indptr)
        assert list(p_indices) == list(w_indices)

    @given(data=weighted_graph(min_vertex_weight=1), nparts=st.integers(2, 4))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_weighted_graph_partitions_like_any_other(self, data, nparts):
        """
        Property (real workflow): a weighted from_edges graph partitions into a
        valid assignment covering every vertex.
        """
        num_vertices, edges, vertex_weights, edge_weights = data
        assume(nparts <= num_vertices)
        graph = Graph.from_edges(
            edges, num_vertices=num_vertices, vertex_weights=vertex_weights, edge_weights=edge_weights
        )
        parts = graph.partition(nparts)
        assert len(parts) == num_vertices
        assert parts.min() >= 0 and parts.max() < nparts


class TestFromEdgesRejectsInvalidInput:
    """Property tests: from_edges refuses, at any position and in any
    orientation, every input that would build a graph failing its own check()."""

    @given(graph_data=simple_graph(min_vertices=2, max_vertices=20), data=st.data())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_duplicate_edge_in_any_orientation_is_rejected(self, graph_data, data):
        num_vertices, edges = graph_data
        u, v = data.draw(st.sampled_from(edges))
        dup = (u, v) if data.draw(st.booleans()) else (v, u)
        position = data.draw(st.integers(min_value=0, max_value=len(edges)))
        with_dup = edges[:position] + [dup] + edges[position:]
        with pytest.raises(ValueError, match="duplicate"):
            Graph.from_edges(with_dup, num_vertices=num_vertices)

    @given(graph_data=simple_graph(min_vertices=2, max_vertices=20), data=st.data())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_self_loop_anywhere_is_rejected(self, graph_data, data):
        num_vertices, edges = graph_data
        v = data.draw(st.integers(min_value=0, max_value=num_vertices - 1))
        position = data.draw(st.integers(min_value=0, max_value=len(edges)))
        with_loop = edges[:position] + [(v, v)] + edges[position:]
        with pytest.raises(ValueError, match="self-loop"):
            Graph.from_edges(with_loop, num_vertices=num_vertices)

    @given(data=weighted_graph(), bad=st.data())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_non_positive_edge_weight_anywhere_is_rejected(self, data, bad):
        """Scotch edge loads must be strictly positive (graph_check.c)."""
        num_vertices, edges, _, edge_weights = data
        k = bad.draw(st.integers(min_value=0, max_value=len(edges) - 1))
        edge_weights = list(edge_weights)
        edge_weights[k] = bad.draw(st.integers(min_value=-5, max_value=0))
        with pytest.raises(ValueError):
            Graph.from_edges(edges, num_vertices=num_vertices, edge_weights=edge_weights)

    @given(data=weighted_graph(), bad=st.data())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_negative_vertex_weight_anywhere_is_rejected(self, data, bad):
        """Vertex loads may be zero but never negative."""
        num_vertices, edges, vertex_weights, _ = data
        k = bad.draw(st.integers(min_value=0, max_value=num_vertices - 1))
        vertex_weights = list(vertex_weights)
        vertex_weights[k] = bad.draw(st.integers(min_value=-5, max_value=-1))
        with pytest.raises(ValueError, match="non-negative"):
            Graph.from_edges(edges, num_vertices=num_vertices, vertex_weights=vertex_weights)

    @given(data=weighted_graph(), extra=st.integers(min_value=1, max_value=3))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_weight_length_mismatch_is_rejected(self, data, extra):
        num_vertices, edges, vertex_weights, edge_weights = data
        with pytest.raises(ValueError, match="edge_weights length"):
            Graph.from_edges(edges, num_vertices=num_vertices, edge_weights=edge_weights + [1] * extra)
        with pytest.raises(ValueError, match="vertex_weights length"):
            Graph.from_edges(edges, num_vertices=num_vertices, vertex_weights=vertex_weights[:-1])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
