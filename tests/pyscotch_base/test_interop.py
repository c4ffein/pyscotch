"""
Unit tests for scipy.sparse and networkx interoperability on Graph.
"""

import numpy as np
import pytest
from pyscotch import Graph


@pytest.fixture
def sparse():
    """The scipy.sparse module (skips the test when scipy is not installed)."""
    return pytest.importorskip("scipy.sparse")


@pytest.fixture
def nx():
    """The networkx module (skips the test when networkx is not installed)."""
    return pytest.importorskip("networkx")


def _path4_csr(sparse):
    """Unweighted path graph 0-1-2-3 as a canonical CSR matrix."""
    dense = np.array(
        [
            [0, 1, 0, 0],
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
        ]
    )
    return sparse.csr_matrix(dense)


def _weighted3_csr(sparse):
    """Weighted path graph 0-1-2 (weights 2 and 5) as a canonical CSR matrix."""
    dense = np.array(
        [
            [0, 2, 0],
            [2, 0, 5],
            [0, 5, 0],
        ]
    )
    return sparse.csr_matrix(dense)


class TestFromScipySparse:
    """Test Graph.from_scipy_sparse."""

    def test_unweighted_csr(self, sparse):
        """Test building from an unweighted CSR matrix."""
        graph = Graph.from_scipy_sparse(_path4_csr(sparse))
        assert graph.check() is True
        assert graph.size() == (4, 6)  # 3 undirected edges = 6 arcs

    def test_weighted_csr(self, sparse):
        """Test building from a weighted CSR matrix (values become edge loads)."""
        graph = Graph.from_scipy_sparse(_weighted3_csr(sparse))
        assert graph.check() is True
        assert graph.size() == (3, 4)
        stats = graph.stat()
        assert stats["edlomin"] == 2
        assert stats["edlomax"] == 5
        assert stats["edlosum"] == 14  # 2 + 2 + 5 + 5 (per arc)

    def test_coo_input(self, sparse):
        """Test that COO input is accepted and equals the CSR result."""
        A = _weighted3_csr(sparse)
        graph = Graph.from_scipy_sparse(A.tocoo())
        assert graph.check() is True
        B = graph.to_scipy_sparse()
        assert (A != B).nnz == 0

    def test_csc_input(self, sparse):
        """Test that CSC input is accepted and equals the CSR result."""
        A = _weighted3_csr(sparse)
        graph = Graph.from_scipy_sparse(A.tocsc())
        assert graph.check() is True
        B = graph.to_scipy_sparse()
        assert (A != B).nnz == 0

    def test_lil_input(self, sparse):
        """Test that LIL input is accepted and equals the CSR result."""
        A = _weighted3_csr(sparse)
        graph = Graph.from_scipy_sparse(A.tolil())
        assert graph.check() is True
        B = graph.to_scipy_sparse()
        assert (A != B).nnz == 0

    def test_dense_input_raises(self, sparse):
        """Test that a dense numpy array is rejected."""
        with pytest.raises(TypeError, match="sparse"):
            Graph.from_scipy_sparse(np.zeros((3, 3)))

    def test_non_square_raises(self, sparse):
        """Test that a non-square matrix is rejected."""
        A = sparse.csr_matrix(np.ones((2, 3)))
        with pytest.raises(ValueError, match="square"):
            Graph.from_scipy_sparse(A)

    def test_asymmetric_structure_raises(self, sparse):
        """Test that a structurally asymmetric matrix is rejected."""
        dense = np.array(
            [
                [0, 1, 0],
                [0, 0, 1],
                [0, 0, 0],
            ]
        )
        A = sparse.csr_matrix(dense)
        with pytest.raises(ValueError, match="symmetric") as excinfo:
            Graph.from_scipy_sparse(A)
        # The error message must suggest how to symmetrize
        assert "A.T" in str(excinfo.value)

    def test_asymmetric_values_raises(self, sparse):
        """Test that symmetric structure with asymmetric values is rejected."""
        dense = np.array(
            [
                [0, 2, 0],
                [3, 0, 1],
                [0, 1, 0],
            ]
        )
        A = sparse.csr_matrix(dense)
        with pytest.raises(ValueError, match="symmetric"):
            Graph.from_scipy_sparse(A)

    def test_self_loop_raises_by_default(self, sparse):
        """Test that a self-loop (nonzero diagonal) raises by default."""
        dense = np.array(
            [
                [1, 1],
                [1, 0],
            ]
        )
        A = sparse.csr_matrix(dense)
        with pytest.raises(ValueError, match="self-loop"):
            Graph.from_scipy_sparse(A)

    def test_self_loop_dropped_with_flag(self, sparse):
        """Test that drop_self_loops=True removes diagonal entries."""
        dense = np.array(
            [
                [1, 1],
                [1, 3],
            ]
        )
        A = sparse.csr_matrix(dense)
        graph = Graph.from_scipy_sparse(A, drop_self_loops=True)
        assert graph.check() is True
        assert graph.size() == (2, 2)  # only the 0-1 edge remains
        B = graph.to_scipy_sparse()
        expected = sparse.csr_matrix(np.array([[0, 1], [1, 0]]))
        assert (B != expected).nnz == 0

    def test_non_integral_float_weights_raise(self, sparse):
        """Test that non-integral float weights are rejected."""
        dense = np.array(
            [
                [0.0, 1.5],
                [1.5, 0.0],
            ]
        )
        A = sparse.csr_matrix(dense)
        with pytest.raises(ValueError, match="integ"):
            Graph.from_scipy_sparse(A)

    def test_integral_float_weights_accepted(self, sparse):
        """Test that integral float weights (e.g. 2.0) are accepted."""
        dense = np.array(
            [
                [0.0, 2.0],
                [2.0, 0.0],
            ]
        )
        A = sparse.csr_matrix(dense)
        graph = Graph.from_scipy_sparse(A)
        assert graph.check() is True
        assert graph.stat()["edlosum"] == 4  # 2 per arc

    def test_negative_weight_raises(self, sparse):
        """Test that negative weights are rejected."""
        dense = np.array(
            [
                [0, -1],
                [-1, 0],
            ]
        )
        A = sparse.csr_matrix(dense)
        with pytest.raises(ValueError, match="positive"):
            Graph.from_scipy_sparse(A)

    def test_zero_weight_raises(self, sparse):
        """Test that explicitly stored zero weights are rejected."""
        # Build via COO so the zero entries stay explicitly stored
        data = np.array([0, 0, 2, 2])
        rows = np.array([0, 1, 1, 2])
        cols = np.array([1, 0, 2, 1])
        A = sparse.csr_matrix((data, (rows, cols)), shape=(3, 3))
        assert A.nnz == 4  # zeros are stored
        with pytest.raises(ValueError, match="positive"):
            Graph.from_scipy_sparse(A)

    def test_use_edge_weights_false_ignores_values(self, sparse):
        """Test that use_edge_weights=False builds an unweighted graph."""
        graph = Graph.from_scipy_sparse(_weighted3_csr(sparse), use_edge_weights=False)
        assert graph.check() is True
        assert graph.size() == (3, 4)
        B = graph.to_scipy_sparse()
        assert np.array_equal(B.data, np.ones(4, dtype=B.data.dtype))

    def test_isolated_vertex(self, sparse):
        """Test that zero rows (isolated vertices) are handled."""
        dense = np.array(
            [
                [0, 1, 0],
                [1, 0, 0],
                [0, 0, 0],
            ]
        )
        A = sparse.csr_matrix(dense)
        graph = Graph.from_scipy_sparse(A)
        assert graph.check() is True
        assert graph.size() == (3, 2)
        B = graph.to_scipy_sparse()
        assert (A != B).nnz == 0

    def test_bool_matrix(self, sparse):
        """Test that a boolean adjacency matrix builds an unweighted graph."""
        A = sparse.csr_matrix(_path4_csr(sparse), dtype=bool)
        graph = Graph.from_scipy_sparse(A)
        assert graph.check() is True
        assert graph.size() == (4, 6)

    def test_duplicate_entries_are_summed(self, sparse):
        """Test that duplicate COO entries are summed before building."""
        data = np.array([1, 1, 1, 1])
        rows = np.array([0, 0, 1, 1])
        cols = np.array([1, 1, 0, 0])
        A = sparse.coo_matrix((data, (rows, cols)), shape=(2, 2))
        graph = Graph.from_scipy_sparse(A)
        assert graph.check() is True
        assert graph.size() == (2, 2)
        assert graph.stat()["edlosum"] == 4  # weight 2 per arc


class TestToScipySparse:
    """Test Graph.to_scipy_sparse."""

    def test_roundtrip_unweighted_exact(self, sparse):
        """Test exact round-trip equality for an unweighted CSR matrix."""
        A = _path4_csr(sparse)
        B = Graph.from_scipy_sparse(A).to_scipy_sparse()
        assert B.shape == A.shape
        assert np.array_equal(B.indptr, A.indptr)
        assert np.array_equal(B.indices, A.indices)
        assert np.array_equal(B.data, A.data)
        assert (A != B).nnz == 0

    def test_roundtrip_weighted_exact(self, sparse):
        """Test exact round-trip equality (structure and weights)."""
        A = _weighted3_csr(sparse)
        B = Graph.from_scipy_sparse(A).to_scipy_sparse()
        assert B.shape == A.shape
        assert np.array_equal(B.indptr, A.indptr)
        assert np.array_equal(B.indices, A.indices)
        assert np.array_equal(B.data, A.data)
        assert (A != B).nnz == 0

    def test_from_edges_graph_export(self, sparse):
        """Test exporting a graph that was not built from scipy."""
        graph = Graph.from_edges([(0, 1), (1, 2), (2, 0)], num_vertices=3)
        B = graph.to_scipy_sparse()
        assert B.shape == (3, 3)
        assert B.nnz == 6
        assert np.array_equal(np.asarray(B.data), np.ones(6, dtype=B.data.dtype))
        assert (B != B.T).nnz == 0  # export is symmetric

    def test_export_is_symmetric(self, sparse):
        """Test that any exported adjacency matrix is symmetric."""
        edges = [(i, (i + 1) % 6) for i in range(6)]
        graph = Graph.from_edges(edges, num_vertices=6)
        B = graph.to_scipy_sparse()
        assert (B != B.T).nnz == 0


class TestFromNetworkx:
    """Test Graph.from_networkx."""

    def _weighted_string_graph(self, nx):
        G = nx.Graph()
        G.add_edge("a", "b", weight=2)
        G.add_edge("b", "c", weight=3)
        return G

    def test_basic_with_string_labels(self, nx):
        """Test building from a graph with string node labels."""
        G = self._weighted_string_graph(nx)
        graph, nodes = Graph.from_networkx(G)
        assert graph.check() is True
        assert graph.size() == (3, 4)
        assert nodes == list(G.nodes())
        assert nodes == ["a", "b", "c"]

    def test_weights_applied(self, nx):
        """Test that edge weights become Scotch edge loads."""
        G = self._weighted_string_graph(nx)
        graph, _ = Graph.from_networkx(G)
        stats = graph.stat()
        assert stats["edlomin"] == 2
        assert stats["edlomax"] == 3
        assert stats["edlosum"] == 10  # 2 + 2 + 3 + 3 (per arc)

    def test_digraph_raises(self, nx):
        """Test that a directed graph is rejected with a conversion hint."""
        G = nx.DiGraph()
        G.add_edge(0, 1)
        with pytest.raises(TypeError, match="to_undirected"):
            Graph.from_networkx(G)

    def test_multigraph_raises(self, nx):
        """Test that a multigraph is rejected with a conversion hint."""
        G = nx.MultiGraph()
        G.add_edge(0, 1)
        G.add_edge(0, 1)
        with pytest.raises(TypeError, match=r"nx\.Graph"):
            Graph.from_networkx(G)

    def test_self_loop_raises(self, nx):
        """Test that self-loops are rejected."""
        G = nx.Graph()
        G.add_edge(0, 1)
        G.add_edge(0, 0)
        with pytest.raises(ValueError, match="self-loop"):
            Graph.from_networkx(G)

    def test_weight_none_disables_weights(self, nx):
        """Test that weight=None ignores edge weight attributes."""
        G = self._weighted_string_graph(nx)
        graph, nodes = Graph.from_networkx(G, weight=None)
        assert graph.check() is True
        H = graph.to_networkx(nodes=nodes)
        for _, _, attrs in H.edges(data=True):
            assert "weight" not in attrs

    def test_missing_weight_attr_defaults_to_one(self, nx):
        """Test that edges missing the weight attribute default to weight 1."""
        G = nx.Graph()
        G.add_edge(0, 1, weight=3)
        G.add_edge(1, 2)  # no weight attribute
        graph, _ = Graph.from_networkx(G)
        stats = graph.stat()
        assert stats["edlomin"] == 1
        assert stats["edlomax"] == 3
        assert stats["edlosum"] == 8  # 3 + 3 + 1 + 1

    def test_no_weight_attrs_builds_unweighted(self, nx):
        """Test that a graph without weight attributes is unweighted."""
        G = nx.Graph([(0, 1), (1, 2)])
        graph, nodes = Graph.from_networkx(G)
        assert graph.check() is True
        H = graph.to_networkx(nodes=nodes)
        for _, _, attrs in H.edges(data=True):
            assert "weight" not in attrs

    def test_all_one_weights_treated_as_unweighted(self, nx):
        """Test that all-ones weights build an unweighted graph."""
        G = nx.Graph()
        G.add_edge(0, 1, weight=1)
        G.add_edge(1, 2, weight=1)
        graph, nodes = Graph.from_networkx(G)
        H = graph.to_networkx(nodes=nodes)
        for _, _, attrs in H.edges(data=True):
            assert "weight" not in attrs

    def test_non_integral_weight_raises(self, nx):
        """Test that non-integral float weights are rejected."""
        G = nx.Graph()
        G.add_edge(0, 1, weight=0.5)
        with pytest.raises(ValueError, match="integ"):
            Graph.from_networkx(G)

    def test_negative_weight_raises(self, nx):
        """Test that negative weights are rejected."""
        G = nx.Graph()
        G.add_edge(0, 1, weight=-2)
        with pytest.raises(ValueError, match="positive"):
            Graph.from_networkx(G)

    def test_zero_weight_raises(self, nx):
        """Test that zero weights are rejected."""
        G = nx.Graph()
        G.add_edge(0, 1, weight=0)
        with pytest.raises(ValueError, match="positive"):
            Graph.from_networkx(G)

    def test_isolated_node(self, nx):
        """Test that isolated nodes are preserved."""
        G = nx.Graph()
        G.add_edge("a", "b")
        G.add_node("z")
        graph, nodes = Graph.from_networkx(G)
        assert graph.check() is True
        assert graph.size() == (3, 2)
        assert "z" in nodes


class TestToNetworkx:
    """Test Graph.to_networkx."""

    def test_roundtrip_labels_and_weights(self, nx):
        """Test round-trip preserving string node labels and edge weights."""
        G = nx.Graph()
        G.add_edge("a", "b", weight=2)
        G.add_edge("b", "c", weight=3)
        G.add_node("z")
        graph, nodes = Graph.from_networkx(G)
        H = graph.to_networkx(nodes=nodes)
        assert set(H.nodes()) == set(G.nodes())
        assert H.number_of_edges() == G.number_of_edges()
        for u, v, attrs in G.edges(data=True):
            assert H.has_edge(u, v)
            assert H[u][v]["weight"] == attrs["weight"]

    def test_default_integer_labels(self, nx):
        """Test that default node labels are 0..n-1."""
        graph = Graph.from_edges([(0, 1), (1, 2), (2, 0)], num_vertices=3)
        H = graph.to_networkx()
        assert set(H.nodes()) == {0, 1, 2}
        assert H.number_of_edges() == 3

    def test_nodes_length_mismatch_raises(self, nx):
        """Test that a wrong-sized nodes list is rejected."""
        graph = Graph.from_edges([(0, 1), (1, 2)], num_vertices=3)
        with pytest.raises(ValueError, match="labels"):
            graph.to_networkx(nodes=["a", "b"])


class TestInteropEndToEnd:
    """End-to-end tests combining interop with partitioning/ordering."""

    def test_karate_club_partition(self, nx):
        """Test nx.karate_club_graph -> from_networkx -> partition(2)."""
        G = nx.karate_club_graph()
        graph, nodes = Graph.from_networkx(G)
        assert graph.check() is True
        assert len(nodes) == G.number_of_nodes()

        parts = graph.partition(2)
        assert len(parts) == G.number_of_nodes()
        # Every vertex gets a part in {0, 1}
        assert set(int(p) for p in np.unique(parts)) <= {0, 1}
        # Both parts non-empty
        assert (parts == 0).any()
        assert (parts == 1).any()

    def test_scipy_partition(self, sparse):
        """Test scipy CSR -> from_scipy_sparse -> partition(2)."""
        # Ring graph on 12 vertices
        n = 12
        rows = np.concatenate([np.arange(n), np.arange(n)])
        cols = np.concatenate([(np.arange(n) + 1) % n, (np.arange(n) - 1) % n])
        A = sparse.csr_matrix((np.ones(2 * n), (rows, cols)), shape=(n, n))
        graph = Graph.from_scipy_sparse(A)
        assert graph.check() is True

        parts = graph.partition(2)
        assert len(parts) == n
        assert set(int(p) for p in np.unique(parts)) <= {0, 1}
        assert (parts == 0).any()
        assert (parts == 1).any()

    def test_scipy_order(self, sparse):
        """Test scipy CSR -> from_scipy_sparse -> order() gives a valid permutation."""
        A = _path4_csr(sparse)
        graph = Graph.from_scipy_sparse(A)
        permutation, inverse = graph.order()
        assert sorted(permutation) == list(range(4))
        assert sorted(inverse) == list(range(4))
        assert graph.order_check(permutation, inverse) is True
