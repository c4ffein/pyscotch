"""
Geometry class for Scotch geometric operations.
"""

from ctypes import byref, POINTER, c_double

from . import libscotch as lib


class Geometry:
    """
    Represents geometry data associated with a graph or mesh.

    Geometry provides coordinate information for vertices, used by
    geometric partitioning algorithms and visualization.
    """

    def __init__(self):
        """Initialize an empty geometry."""
        self._geom = lib.SCOTCH_Geom()
        ret = lib.SCOTCH_geomInit(byref(self._geom))
        if ret != 0:
            raise RuntimeError(f"SCOTCH_geomInit failed with error {ret}")
        self._initialized = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        """Release geometry resources. Called automatically when used as a context manager."""
        if getattr(self, "_initialized", False):
            lib.SCOTCH_geomExit(byref(self._geom))
            self._initialized = False

    def data(self):
        """
        Get the geometry data.

        Returns:
            Tuple of (dimension, coordinate_pointer)
            - dimension: Number of spatial dimensions (0, 1, 2, or 3)
            - coordinate_pointer: ctypes pointer to coordinate array
        """
        dim = lib.SCOTCH_Num()
        coords = POINTER(c_double)()
        lib.SCOTCH_geomData(byref(self._geom), byref(dim), byref(coords))
        return (dim.value, coords)
