"""
Tests for Mesh advanced methods: to_dual_graph, order.
"""

import pytest
from pathlib import Path

from pyscotch import Mesh


def _load_test_mesh():
    """Load a test mesh from Scotch data, or skip."""
    test_data = Path("external/scotch/src/check/data/small2.msh")
    if not test_data.exists():
        pytest.skip("small2.msh test data not available")
    mesh = Mesh()
    mesh.load(test_data)
    return mesh


class TestMeshDualGraph:
    def test_dual_graph_valid(self):
        mesh = _load_test_mesh()
        dual = mesh.to_dual_graph(ncomm=1)
        v, e = dual.size()
        assert v > 0
        assert dual.check()


class TestMeshOrder:
    def test_order_returns_permutation(self):
        mesh = _load_test_mesh()
        perm, inv = mesh.order()
        assert len(perm) > 0
        assert len(inv) == len(perm)
