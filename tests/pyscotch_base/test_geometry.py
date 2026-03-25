"""
Tests for Geometry class.
"""

from pyscotch import Geometry


class TestGeometry:
    def test_create_empty(self):
        geom = Geometry()
        dim, coords = geom.data()
        assert dim == 0
