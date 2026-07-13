"""
Tests for Mesh advanced methods: to_dual_graph, order.
"""

import numpy as np
import pytest
from pathlib import Path

from pyscotch import Mesh
from pyscotch import libscotch as lib


def _load_test_mesh():
    """Load a test mesh from Scotch data, or skip."""
    test_data = Path("external/scotch/src/check/data/small2.msh")
    if not test_data.exists():
        pytest.skip("small2.msh test data not available")
    mesh = Mesh()
    mesh.load(test_data)
    return mesh


def _build_two_triangles_shared_edge():
    """Two triangle elements sharing an edge (two common nodes).

    Elements 0, 1; nodes 2..5 (A=2, B=3, C=4, D=5).
    Element 0 = {A, B, C}, element 1 = {B, C, D}.
    """
    dtype = lib.get_scotch_dtype()
    verttab = np.array([0, 3, 6, 7, 9, 11, 12], dtype=dtype)
    edgetab = np.array([2, 3, 4, 3, 4, 5, 0, 0, 1, 0, 1, 1], dtype=dtype)
    mesh = Mesh()
    mesh.build(2, 4, verttab, edgetab, velmbas=0, vnodbas=2)
    return mesh


def _build_two_triangles_shared_node():
    """Two triangle elements sharing a single node.

    Elements 0, 1; nodes 2..6 (A=2, B=3, C=4, D=5, E=6).
    Element 0 = {A, B, C}, element 1 = {C, D, E}.
    """
    dtype = lib.get_scotch_dtype()
    verttab = np.array([0, 3, 6, 7, 8, 10, 11, 12], dtype=dtype)
    edgetab = np.array([2, 3, 4, 4, 5, 6, 0, 0, 0, 1, 1, 1], dtype=dtype)
    mesh = Mesh()
    mesh.build(2, 5, verttab, edgetab, velmbas=0, vnodbas=2)
    return mesh


def _assert_valid_ordering(perm, inv):
    """perm must be a permutation of 0..n-1 and inv its inverse."""
    n = len(perm)
    assert len(inv) == n
    assert sorted(perm) == list(range(n))
    assert all(perm[inv[i]] == i for i in range(n))


class TestMeshDualGraph:
    def test_dual_graph_valid(self):
        mesh = _load_test_mesh()
        dual = mesh.to_dual_graph(ncomm=1)
        v, e = dual.size()
        assert v > 0
        assert dual.check()

    def test_dual_shared_edge_hand_checked(self):
        # Two triangles sharing 2 nodes: dual has one vertex per element and
        # one (bidirectional) edge between them
        mesh = _build_two_triangles_shared_edge()
        assert mesh.check()

        dual = mesh.to_dual_graph(ncomm=1)
        assert dual.check()
        assert dual.size() == (2, 2)

        dual2 = mesh.to_dual_graph(ncomm=2)
        assert dual2.size() == (2, 2)

    def test_dual_shared_node_threshold(self):
        # Two triangles sharing exactly 1 node. Adjacency threshold is
        # min(ncomm, degree(e1) - 1, degree(e2) - 1) shared nodes
        # (see meshGraphDual in mesh_graph.c), i.e. min(ncomm, 2) here:
        # ncomm=1 -> adjacent, ncomm=2 -> not adjacent
        mesh = _build_two_triangles_shared_node()
        assert mesh.check()

        dual1 = mesh.to_dual_graph(ncomm=1)
        assert dual1.check()
        assert dual1.size() == (2, 2)

        dual2 = mesh.to_dual_graph(ncomm=2)
        assert dual2.check()
        assert dual2.size() == (2, 0)


class TestMeshOrder:
    def test_order_returns_permutation(self):
        mesh = _load_test_mesh()
        perm, inv = mesh.order()
        assert len(perm) > 0
        _assert_valid_ordering(perm, inv)

    def test_order_built_mesh(self):
        # Node ordering of a hand-built mesh: one entry per node
        mesh = _build_two_triangles_shared_edge()
        perm, inv = mesh.order()
        assert len(perm) == 4
        _assert_valid_ordering(perm, inv)
