"""
Tests for Architecture class: topologies, save/load, sub-architecture.
"""

import numpy as np
import pytest
import tempfile
import os

from pyscotch import Architecture
from pyscotch import libscotch as lib


def _scotch_array(values):
    return np.array(values, dtype=lib.get_scotch_dtype())


class TestArchitectureTopologies:
    def test_hypercube(self):
        arch = Architecture()
        arch.hypercube(3)
        assert arch.name() == "hcub"
        assert arch.size() == 8

    def test_mesh2d(self):
        arch = Architecture()
        arch.mesh2d(4, 3)
        assert arch.name() == "mesh2D"
        assert arch.size() == 12

    def test_mesh3d(self):
        arch = Architecture()
        arch.mesh3d(2, 3, 4)
        assert arch.name() == "mesh3D"
        assert arch.size() == 24

    def test_torus2d(self):
        arch = Architecture()
        arch.torus2d(3, 4)
        assert arch.name() == "torus2D"
        assert arch.size() == 12

    def test_torus3d(self):
        arch = Architecture()
        arch.torus3d(2, 2, 2)
        assert arch.name() == "torus3D"
        assert arch.size() == 8

    def test_tree_leaf(self):
        arch = Architecture()
        scotch_dtype = lib.get_scotch_dtype()
        sizes = np.array([2, 3], dtype=scotch_dtype)
        links = np.array([10, 1], dtype=scotch_dtype)
        arch.tree_leaf(2, sizes, links)
        assert arch.name() == "tleaf"
        assert arch.size() == 6

    def test_variable_complete(self):
        arch = Architecture()
        arch.variable_complete()
        assert arch.name() == "varcmplt"

    def test_variable_hypercube(self):
        arch = Architecture()
        arch.variable_hypercube()
        assert arch.name() == "varhcub"

    def test_complete_weighted(self):
        arch = Architecture()
        scotch_dtype = lib.get_scotch_dtype()
        weights = np.array([1, 2, 3, 4], dtype=scotch_dtype)
        arch.complete_weighted(4, weights)
        assert arch.name() == "cmpltw"
        assert arch.size() == 4


class TestArchitectureSubAndIO:
    def test_sub_architecture(self):
        parent = Architecture()
        parent.complete(8)

        child = Architecture()
        scotch_dtype = lib.get_scotch_dtype()
        vlist = np.array([0, 2, 4], dtype=scotch_dtype)
        child.sub(parent, vlist)
        assert child.size() == 3

    def test_save_load_roundtrip(self):
        arch = Architecture()
        arch.hypercube(3)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.arch') as f:
            path = f.name
        try:
            arch.save(path)
            arch2 = Architecture()
            arch2.load(path)
            assert arch2.name() == "hcub"
            assert arch2.size() == 8
        finally:
            os.unlink(path)

    @pytest.mark.parametrize("setup,name,size", [
        (lambda a: a.complete(5), "cmplt", 5),
        (lambda a: a.complete_weighted(4, _scotch_array([1, 2, 3, 4])), "cmpltw", 4),
        (lambda a: a.hypercube(3), "hcub", 8),
        (lambda a: a.mesh2d(4, 3), "mesh2D", 12),
        (lambda a: a.mesh3d(2, 3, 4), "mesh3D", 24),
        (lambda a: a.torus2d(3, 4), "torus2D", 12),
        (lambda a: a.torus3d(2, 3, 2), "torus3D", 12),
        (lambda a: a.tree_leaf(2, _scotch_array([2, 3]), _scotch_array([10, 1])), "tleaf", 6),
        (lambda a: a.variable_complete(), "varcmplt", None),
        (lambda a: a.variable_hypercube(), "varhcub", None),
    ])
    def test_save_load_roundtrip_all_topologies(self, setup, name, size):
        arch = Architecture()
        setup(arch)
        assert arch.name() == name
        if size is not None:
            assert arch.size() == size

        with tempfile.NamedTemporaryFile(delete=False, suffix='.arch') as f:
            path = f.name
        try:
            arch.save(path)
            arch2 = Architecture()
            arch2.load(path)
            assert arch2.name() == name
            assert arch2.size() == arch.size()
        finally:
            os.unlink(path)
