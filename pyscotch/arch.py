"""
Architecture class for PT-Scotch target architectures.
"""

import numpy as np
from ctypes import byref, POINTER

from .api_decorators import scotch_binding
from . import libscotch as lib


class Architecture:
    """
    Represents a target architecture for graph mapping.

    An architecture defines the topology of the target machine or domain
    decomposition onto which a graph will be mapped.
    """

    def __init__(self):
        """Initialize an architecture."""
        self._arch = lib.SCOTCH_Arch()
        ret = lib.SCOTCH_archInit(byref(self._arch))
        if ret != 0:
            raise RuntimeError(f"Failed to initialize architecture (error code: {ret})")

        self._initialized = True

    def __del__(self):
        """Clean up architecture resources."""
        if hasattr(self, "_initialized") and self._initialized:
            lib.SCOTCH_archExit(byref(self._arch))

    @scotch_binding("SCOTCH_archName", "char * SCOTCH_archName(const SCOTCH_Arch *)")
    def name(self) -> str:
        """
        Get the name of the architecture type.

        Returns:
            Architecture type name (e.g., "cmplt" for complete graph)
        """
        result = lib.SCOTCH_archName(byref(self._arch))
        if result:
            return result.decode("utf-8")
        return ""

    @scotch_binding("SCOTCH_archSize", "SCOTCH_Num SCOTCH_archSize(const SCOTCH_Arch *)")
    def size(self) -> int:
        """
        Get the number of processors/domains in the architecture.

        Returns:
            Number of processors/domains
        """
        return lib.SCOTCH_archSize(byref(self._arch))

    @scotch_binding("SCOTCH_archCmplt", "int SCOTCH_archCmplt(SCOTCH_Arch *, SCOTCH_Num)")
    def complete(self, size: int) -> None:
        """
        Set up a complete graph architecture.

        A complete graph architecture represents a fully connected topology
        with the specified number of processors/domains.

        Args:
            size: Number of processors/domains

        Raises:
            RuntimeError: If setup fails
        """
        ret = lib.SCOTCH_archCmplt(byref(self._arch), lib.SCOTCH_Num(size))
        if ret != 0:
            raise RuntimeError(f"Failed to create complete architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archCmpltw", "int SCOTCH_archCmpltw(SCOTCH_Arch *, SCOTCH_Num, SCOTCH_Num *)")
    def complete_weighted(self, size: int, weights: np.ndarray) -> None:
        """
        Set up a weighted complete graph architecture.

        Args:
            size: Number of processors/domains
            weights: Array of processor weights (length must equal size)

        Raises:
            ValueError: If weights length doesn't match size
            RuntimeError: If setup fails
        """
        if len(weights) != size:
            raise ValueError(f"weights length ({len(weights)}) must match size ({size})")
        scotch_dtype = lib.get_scotch_dtype()
        weights_arr = np.asarray(weights, dtype=scotch_dtype)
        weights_c = weights_arr.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        ret = lib.SCOTCH_archCmpltw(byref(self._arch), lib.SCOTCH_Num(size), weights_c)
        if ret != 0:
            raise RuntimeError(f"Failed to create weighted complete architecture (error code: {ret})")

    @staticmethod
    def complete_graph(size: int) -> "Architecture":
        """
        Create a complete graph architecture.

        Args:
            size: Number of processors/domains

        Returns:
            New Architecture instance
        """
        arch = Architecture()
        arch.complete(size)
        return arch
