"""
Mesh class for PT-Scotch mesh operations.
"""

import numpy as np
from ctypes import byref, POINTER, c_void_p
from pathlib import Path
from typing import Union, Optional, Tuple

try:
    from . import libscotch as lib
    _lib_available = lib._libscotch is not None
except ImportError:
    _lib_available = False


class Mesh:
    """
    Represents a mesh structure for partitioning.

    A mesh consists of elements (cells) and nodes. This class provides methods to:
    - Load meshes from files
    - Build meshes from arrays
    - Partition meshes
    - Convert meshes to graphs
    """

    def __init__(self):
        """Initialize an empty mesh."""
        if not _lib_available:
            raise RuntimeError(
                "Scotch library not available. Build it with 'make build-scotch'"
            )

        self._mesh = lib.SCOTCH_Mesh()
        ret = lib.SCOTCH_meshInit(byref(self._mesh))
        if ret != 0:
            raise RuntimeError(f"Failed to initialize mesh (error code: {ret})")

        self._initialized = True

    def __del__(self):
        """Clean up mesh resources."""
        if hasattr(self, "_initialized") and self._initialized:
            lib.SCOTCH_meshExit(byref(self._mesh))

    def load(self, filename: Union[str, Path]) -> None:
        """
        Load a mesh from a file in Scotch mesh format.

        Args:
            filename: Path to the mesh file (.msh format)

        Raises:
            FileNotFoundError: If the file doesn't exist
            RuntimeError: If loading fails
        """
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"Mesh file not found: {filename}")

        # Open file and get file pointer
        import ctypes.util
        file_ptr = open(str(filename), "rb")
        try:
            if hasattr(ctypes, 'pythonapi'):
                PyFile_AsFile = ctypes.pythonapi.PyFile_AsFile
                PyFile_AsFile.argtypes = [ctypes.py_object]
                PyFile_AsFile.restype = ctypes.c_void_p
                c_file = PyFile_AsFile(file_ptr)
            else:
                libc = ctypes.CDLL(ctypes.util.find_library("c"))
                c_file = libc.fdopen(file_ptr.fileno(), b"r")

            baseval = lib.SCOTCH_Num(0)
            ret = lib.SCOTCH_meshLoad(byref(self._mesh), c_file, baseval)

            if ret != 0:
                raise RuntimeError(f"Failed to load mesh from {filename} (error code: {ret})")
        finally:
            file_ptr.close()

    def save(self, filename: Union[str, Path]) -> None:
        """
        Save the mesh to a file in Scotch mesh format.

        Args:
            filename: Output file path

        Raises:
            RuntimeError: If saving fails
        """
        filename = Path(filename)
        file_ptr = open(str(filename), "wb")
        try:
            import ctypes.util
            if hasattr(ctypes, 'pythonapi'):
                PyFile_AsFile = ctypes.pythonapi.PyFile_AsFile
                PyFile_AsFile.argtypes = [ctypes.py_object]
                PyFile_AsFile.restype = ctypes.c_void_p
                c_file = PyFile_AsFile(file_ptr)
            else:
                libc = ctypes.CDLL(ctypes.util.find_library("c"))
                c_file = libc.fdopen(file_ptr.fileno(), b"w")

            ret = lib.SCOTCH_meshSave(byref(self._mesh), c_file)

            if ret != 0:
                raise RuntimeError(f"Failed to save mesh to {filename} (error code: {ret})")
        finally:
            file_ptr.close()

    def build(
        self,
        velmnbr: int,
        vnodnbr: int,
        verttab: np.ndarray,
        edgetab: np.ndarray,
        velotab: Optional[np.ndarray] = None,
        vnlotab: Optional[np.ndarray] = None,
        velmbas: int = 0,
        vnodbas: int = 0,
    ) -> None:
        """
        Build a mesh from arrays.

        Args:
            velmnbr: Number of elements
            vnodnbr: Number of nodes
            verttab: Vertex array (connectivity information)
            edgetab: Edge array (node indices for elements)
            velotab: Element weights (optional)
            vnlotab: Node weights (optional)
            velmbas: Base value for element indexing
            vnodbas: Base value for node indexing

        Raises:
            RuntimeError: If building fails
        """
        edgenbr = len(edgetab)

        # Convert to ctypes arrays
        verttab_c = verttab.astype(np.int64).ctypes.data_as(POINTER(lib.SCOTCH_Num))
        edgetab_c = edgetab.astype(np.int64).ctypes.data_as(POINTER(lib.SCOTCH_Num))

        velotab_c = velotab.astype(np.int64).ctypes.data_as(POINTER(lib.SCOTCH_Num)) if velotab is not None else None
        vnlotab_c = vnlotab.astype(np.int64).ctypes.data_as(POINTER(lib.SCOTCH_Num)) if vnlotab is not None else None

        ret = lib.SCOTCH_meshBuild(
            byref(self._mesh),
            lib.SCOTCH_Num(velmbas),
            lib.SCOTCH_Num(vnodbas),
            lib.SCOTCH_Num(velmnbr),
            lib.SCOTCH_Num(vnodnbr),
            verttab_c,
            None,  # vendtab
            velotab_c,
            vnlotab_c,
            None,  # vlbltab
            lib.SCOTCH_Num(edgenbr),
            edgetab_c,
        )

        if ret != 0:
            raise RuntimeError(f"Failed to build mesh (error code: {ret})")

    def check(self) -> bool:
        """
        Check the consistency of the mesh structure.

        Returns:
            True if the mesh is valid, False otherwise
        """
        ret = lib.SCOTCH_meshCheck(byref(self._mesh))
        return ret == 0

    def to_graph(self):
        """
        Convert the mesh to a graph representation.

        Returns:
            Graph object representing the mesh's dual graph

        Raises:
            RuntimeError: If conversion fails
        """
        from .graph import Graph

        graph = Graph()
        ret = lib.SCOTCH_meshGraph(byref(self._mesh), byref(graph._graph))

        if ret != 0:
            raise RuntimeError(f"Failed to convert mesh to graph (error code: {ret})")

        return graph

    def partition(
        self,
        nparts: int,
        strategy=None,
    ) -> np.ndarray:
        """
        Partition the mesh into a specified number of parts.

        This converts the mesh to a graph and partitions it.

        Args:
            nparts: Number of partitions
            strategy: Partitioning strategy (optional)

        Returns:
            Array of partition assignments

        Raises:
            RuntimeError: If partitioning fails
        """
        # Convert mesh to graph and partition
        graph = self.to_graph()
        return graph.partition(nparts, strategy)

    def save_mapping(self, filename: Union[str, Path], mapping: np.ndarray) -> None:
        """
        Save a mapping/partition to a file.

        Args:
            filename: Output file path
            mapping: Partition array to save
        """
        filename = Path(filename)
        with open(filename, "w") as f:
            f.write(f"{len(mapping)}\n")
            for i, part in enumerate(mapping):
                f.write(f"{i}\t{part}\n")
