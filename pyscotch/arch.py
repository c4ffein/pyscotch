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
        weights_arr, weights_c = lib.to_scotch_array(weights)
        ret = lib.SCOTCH_archCmpltw(byref(self._arch), lib.SCOTCH_Num(size), weights_c)
        if ret != 0:
            raise RuntimeError(f"Failed to create weighted complete architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archHcub", "int SCOTCH_archHcub(SCOTCH_Arch *, SCOTCH_Num)")
    def hypercube(self, dim: int) -> None:
        """Set up a hypercube architecture with 2^dim processors."""
        ret = lib.SCOTCH_archHcub(byref(self._arch), lib.SCOTCH_Num(dim))
        if ret != 0:
            raise RuntimeError(f"Failed to create hypercube architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archMesh2", "int SCOTCH_archMesh2(SCOTCH_Arch *, SCOTCH_Num, SCOTCH_Num)")
    def mesh2d(self, dim_x: int, dim_y: int) -> None:
        """Set up a 2D mesh architecture."""
        ret = lib.SCOTCH_archMesh2(byref(self._arch), lib.SCOTCH_Num(dim_x), lib.SCOTCH_Num(dim_y))
        if ret != 0:
            raise RuntimeError(f"Failed to create 2D mesh architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archMesh3", "int SCOTCH_archMesh3(SCOTCH_Arch *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num)")
    def mesh3d(self, dim_x: int, dim_y: int, dim_z: int) -> None:
        """Set up a 3D mesh architecture."""
        ret = lib.SCOTCH_archMesh3(
            byref(self._arch),
            lib.SCOTCH_Num(dim_x), lib.SCOTCH_Num(dim_y), lib.SCOTCH_Num(dim_z))
        if ret != 0:
            raise RuntimeError(f"Failed to create 3D mesh architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archTorus2", "int SCOTCH_archTorus2(SCOTCH_Arch *, SCOTCH_Num, SCOTCH_Num)")
    def torus2d(self, dim_x: int, dim_y: int) -> None:
        """Set up a 2D torus architecture."""
        ret = lib.SCOTCH_archTorus2(byref(self._arch), lib.SCOTCH_Num(dim_x), lib.SCOTCH_Num(dim_y))
        if ret != 0:
            raise RuntimeError(f"Failed to create 2D torus architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archTorus3", "int SCOTCH_archTorus3(SCOTCH_Arch *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num)")
    def torus3d(self, dim_x: int, dim_y: int, dim_z: int) -> None:
        """Set up a 3D torus architecture."""
        ret = lib.SCOTCH_archTorus3(
            byref(self._arch),
            lib.SCOTCH_Num(dim_x), lib.SCOTCH_Num(dim_y), lib.SCOTCH_Num(dim_z))
        if ret != 0:
            raise RuntimeError(f"Failed to create 3D torus architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archTleaf", "int SCOTCH_archTleaf(SCOTCH_Arch *, SCOTCH_Num, SCOTCH_Num *, SCOTCH_Num *)")
    def tree_leaf(self, levels: int, sizes: np.ndarray, links: np.ndarray) -> None:
        """
        Set up a tree-leaf architecture.

        Args:
            levels: Number of levels in the tree
            sizes: Array of cluster sizes per level (length = levels)
            links: Array of link weights per level (length = levels)
        """
        sizes_arr, sizes_c = lib.to_scotch_array(sizes)
        links_arr, links_c = lib.to_scotch_array(links)
        ret = lib.SCOTCH_archTleaf(
            byref(self._arch), lib.SCOTCH_Num(levels), sizes_c, links_c)
        if ret != 0:
            raise RuntimeError(f"Failed to create tree-leaf architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archVcmplt", "int SCOTCH_archVcmplt(SCOTCH_Arch *)")
    def variable_complete(self) -> None:
        """Set up a variable-size complete graph architecture."""
        ret = lib.SCOTCH_archVcmplt(byref(self._arch))
        if ret != 0:
            raise RuntimeError(f"Failed to create variable complete architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archVhcub", "int SCOTCH_archVhcub(SCOTCH_Arch *)")
    def variable_hypercube(self) -> None:
        """Set up a variable-size hypercube architecture."""
        ret = lib.SCOTCH_archVhcub(byref(self._arch))
        if ret != 0:
            raise RuntimeError(f"Failed to create variable hypercube architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archSub", "int SCOTCH_archSub(SCOTCH_Arch *, SCOTCH_Arch *, SCOTCH_Num, SCOTCH_Num *)")
    def sub(self, parent: "Architecture", vertex_list: np.ndarray) -> None:
        """
        Create a sub-architecture from a parent architecture.

        Args:
            parent: Parent architecture to extract from
            vertex_list: Array of domain indices to include
        """
        vlist, vlist_c = lib.to_scotch_array(vertex_list)
        ret = lib.SCOTCH_archSub(
            byref(self._arch), byref(parent._arch),
            lib.SCOTCH_Num(len(vlist)), vlist_c)
        if ret != 0:
            raise RuntimeError(f"Failed to create sub-architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archLoad", "int SCOTCH_archLoad(SCOTCH_Arch *, FILE *)")
    def load(self, filename) -> None:
        """Load an architecture from a file."""
        from .graph import c_fopen
        with c_fopen(str(filename), "r") as fp:
            ret = lib.SCOTCH_archLoad(byref(self._arch), fp)
            if ret != 0:
                raise RuntimeError(f"Failed to load architecture (error code: {ret})")

    @scotch_binding("SCOTCH_archSave", "int SCOTCH_archSave(const SCOTCH_Arch *, FILE *)")
    def save(self, filename) -> None:
        """Save the architecture to a file."""
        from .graph import c_fopen
        with c_fopen(str(filename), "w") as fp:
            ret = lib.SCOTCH_archSave(byref(self._arch), fp)
            if ret != 0:
                raise RuntimeError(f"Failed to save architecture (error code: {ret})")

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
