"""
Tests for Geometry class.
"""

from pyscotch import Geometry


class TestGeometry:
    def test_create_empty(self):
        geom = Geometry()
        dim, coords = geom.data()
        assert dim == 0

    def test_close_releases(self):
        geom = Geometry()
        geom.close()
        assert not geom._initialized
        # close() must be idempotent
        geom.close()

    def test_context_manager(self):
        with Geometry() as geom:
            dim, coords = geom.data()
            assert dim == 0
        assert not geom._initialized
