"""
High-level Graph class for PT-Scotch.
"""

import numpy as np
import ctypes
import ctypes.util
from ctypes import byref, c_long, POINTER, cast, c_void_p
from pathlib import Path
from typing import Optional, Union, List, Tuple
from contextlib import contextmanager

try:
    from . import libscotch as lib
    _lib_available = lib._libscotch is not None
except ImportError:
    _lib_available = False


# ============================================================================
# C FILE* Context Manager
# ============================================================================

@contextmanager
def c_fopen(filename: str, mode: str = "r"):
    """
    Context manager for C FILE* pointers using libc's fopen/fclose.

    This avoids Python's file handling entirely, allowing us to pass FILE*
    pointers to Scotch functions without ownership/buffering conflicts.

    Args:
        filename: Path to file
        mode: File mode ("r", "w", "rb", "wb", etc.)

    Yields:
        C FILE* pointer (as ctypes.c_void_p)

    Raises:
        IOError: If file cannot be opened
        RuntimeError: If libc cannot be loaded

    Example:
        with c_fopen("graph.grf", "r") as file_ptr:
            lib.SCOTCH_graphLoad(byref(graph._graph), file_ptr, -1, 0)

    Note on Issue 1 (C runtime mismatch):
        On most Linux systems, both Python and Scotch use glibc, so FILE*
        structure layout is compatible. If you encounter segfaults, you may
        have a C runtime mismatch. Workaround available - contact maintainer.
    """
    # Load libc
    libc_name = ctypes.util.find_library("c")
    if not libc_name:
        raise RuntimeError("Could not find C standard library")

    libc = ctypes.CDLL(libc_name)

    # Configure fopen
    libc.fopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    libc.fopen.restype = ctypes.c_void_p

    # Configure fclose
    libc.fclose.argtypes = [ctypes.c_void_p]
    libc.fclose.restype = ctypes.c_int

    # Open file using C's fopen (Issue 2: Error handling)
    file_ptr = libc.fopen(str(filename).encode(), mode.encode())

    if not file_ptr:
        # Get errno for better error message
        errno_val = ctypes.get_errno()
        raise IOError(f"Failed to open file '{filename}' with mode '{mode}' (errno: {errno_val})")

    try:
        # Yield the FILE* pointer to the caller
        yield file_ptr
    finally:
        # Issue 3: Memory management - always close the file
        if file_ptr:
            libc.fclose(file_ptr)


class Graph:
    """
    Represents a graph structure for partitioning and ordering.

    A graph consists of vertices and edges. This class provides methods to:
    - Load graphs from files
    - Build graphs from arrays
    - Partition graphs
    - Order graphs (for sparse matrix factorization)
    - Map graphs to architectures
    """

    def __init__(self):
        """Initialize an empty graph."""
        if not _lib_available:
            raise RuntimeError(
                "Scotch library not available. Build it with 'make build-scotch'"
            )

        self._graph = lib.SCOTCH_Graph()
        ret = lib.SCOTCH_graphInit(byref(self._graph))
        if ret != 0:
            raise RuntimeError(f"Failed to initialize graph (error code: {ret})")

        self._initialized = True
        # Keep references to arrays to prevent garbage collection
        self._verttab = None
        self._vendtab = None  # Added vendtab reference
        self._edgetab = None
        self._velotab = None
        self._edlotab = None

    def __del__(self):
        """Clean up graph resources."""
        if hasattr(self, "_initialized") and self._initialized:
            lib.SCOTCH_graphExit(byref(self._graph))

    def load(self, filename: Union[str, Path]) -> None:
        """
        Load a graph from a file in Scotch graph format.

        Uses C's fopen() to avoid Python FILE* incompatibility issues.

        Args:
            filename: Path to the graph file (.grf format)

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If file cannot be opened
            RuntimeError: If loading fails
        """
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"Graph file not found: {filename}")

        # Use C fopen context manager - avoids Python file handling issues
        with c_fopen(str(filename), "r") as file_ptr:
            baseval = lib.SCOTCH_Num(0)
            ret = lib.SCOTCH_graphLoad(
                byref(self._graph),
                file_ptr,
                baseval,
                0
            )

            if ret != 0:
                raise RuntimeError(f"Failed to load graph from {filename} (error code: {ret})")

    def save(self, filename: Union[str, Path]) -> None:
        """
        Save the graph to a file in Scotch graph format.

        Uses C's fopen() to avoid Python FILE* incompatibility issues.

        Args:
            filename: Output file path

        Raises:
            IOError: If file cannot be opened
            RuntimeError: If saving fails
        """
        filename = Path(filename)

        # Use C fopen context manager - avoids Python file handling issues
        with c_fopen(str(filename), "w") as file_ptr:
            ret = lib.SCOTCH_graphSave(byref(self._graph), file_ptr)

            if ret != 0:
                raise RuntimeError(f"Failed to save graph to {filename} (error code: {ret})")

    def build(
        self,
        verttab: np.ndarray,
        edgetab: np.ndarray,
        velotab: Optional[np.ndarray] = None,
        edlotab: Optional[np.ndarray] = None,
        baseval: int = 0,
    ) -> None:
        """
        Build a graph from arrays.

        Args:
            verttab: Vertex array (start indices in edgetab for each vertex)
            edgetab: Edge array (adjacent vertices)
            velotab: Vertex weights (optional)
            edlotab: Edge weights (optional)
            baseval: Base value for indexing (0 or 1)

        Raises:
            ValueError: If input arrays are invalid
            RuntimeError: If building fails
        """
        # Input validation
        if len(verttab) < 2:
            raise ValueError("verttab must have at least 2 elements (for 1 vertex)")
        if baseval not in (0, 1):
            raise ValueError(f"baseval must be 0 or 1, got {baseval}")

        vertnbr = len(verttab) - 1
        edgenbr = len(edgetab)

        # Validate vertex weights array size if provided
        if velotab is not None and len(velotab) != vertnbr:
            raise ValueError(
                f"velotab length ({len(velotab)}) must match number of vertices ({vertnbr})"
            )

        # Validate edge weights array size if provided
        if edlotab is not None and len(edlotab) != edgenbr:
            raise ValueError(
                f"edlotab length ({len(edlotab)}) must match number of edges ({edgenbr})"
            )

        # Store arrays to prevent garbage collection
        # Use dtype matching the compiled Scotch library (detected at import)
        scotch_dtype = lib.get_scotch_dtype()
        self._verttab = verttab.astype(scotch_dtype)
        self._edgetab = edgetab.astype(scotch_dtype)
        self._velotab = velotab.astype(scotch_dtype) if velotab is not None else None
        self._edlotab = edlotab.astype(scotch_dtype) if edlotab is not None else None

        # Convert to ctypes arrays
        verttab_c = self._verttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        edgetab_c = self._edgetab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        velotab_c = self._velotab.ctypes.data_as(POINTER(lib.SCOTCH_Num)) if self._velotab is not None else None
        edlotab_c = self._edlotab.ctypes.data_as(POINTER(lib.SCOTCH_Num)) if self._edlotab is not None else None

        # Pass verttab as vendtab to trigger Scotch's (vendtab == verttab) check
        # which automatically uses verttab[i+1] as the end index for vertex i
        ret = lib.SCOTCH_graphBuild(
            byref(self._graph),
            lib.SCOTCH_Num(baseval),
            lib.SCOTCH_Num(vertnbr),
            verttab_c,
            verttab_c,  # Same pointer as verttab - Scotch will use verttab[i+1]
            velotab_c,
            None,  # vlbltab
            lib.SCOTCH_Num(edgenbr),
            edgetab_c,
            edlotab_c,
        )

        if ret != 0:
            raise RuntimeError(
                f"Failed to build graph with {vertnbr} vertices and {edgenbr} edges "
                f"(Scotch error code: {ret})"
            )

    def check(self) -> bool:
        """
        Check the consistency of the graph structure.

        Returns:
            True if the graph is valid, False otherwise
        """
        ret = lib.SCOTCH_graphCheck(byref(self._graph))
        return ret == 0

    def size(self) -> Tuple[int, int]:
        """
        Get the size of the graph.

        Returns:
            Tuple of (number of vertices, number of edges)
        """
        vertnbr = lib.SCOTCH_Num()
        edgenbr = lib.SCOTCH_Num()
        lib.SCOTCH_graphSize(byref(self._graph), byref(vertnbr), byref(edgenbr))
        return (vertnbr.value, edgenbr.value)

    def partition(
        self,
        nparts: int,
        strategy=None,
    ) -> np.ndarray:
        """
        Partition the graph into a specified number of parts.

        Args:
            nparts: Number of partitions
            strategy: Partitioning strategy (optional)

        Returns:
            Array of partition assignments for each vertex

        Raises:
            ValueError: If nparts is invalid
            RuntimeError: If partitioning fails
        """
        if nparts < 1:
            raise ValueError(f"nparts must be at least 1, got {nparts}")

        from .strategy import Strategy
        from .arch import Architecture

        vertnbr, _ = self.size()

        if nparts > vertnbr:
            raise ValueError(
                f"nparts ({nparts}) cannot exceed number of vertices ({vertnbr})"
            )

        # Create partition array (dtype matches compiled Scotch)
        parttab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        parttab_c = parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Create architecture
        arch = Architecture()
        arch.complete(nparts)

        # Use provided strategy or create default (empty) strategy
        # Note: For SCOTCH_graphPart, an empty/unmodified strategy works best
        if strategy is None:
            strategy = Strategy()  # Don't call set_mapping_default() - empty strategy works better

        # Use 3-step API: Init -> Compute -> Exit
        # This is the recommended pattern from Scotch C examples
        mappdat = lib.SCOTCH_Mapping()

        # Step 1: Initialize mapping
        ret = lib.SCOTCH_graphMapInit(
            byref(self._graph),
            byref(mappdat),
            byref(arch._arch),
            parttab_c,
        )
        if ret != 0:
            raise RuntimeError(
                f"Failed to initialize mapping for {nparts} parts "
                f"(Scotch error code: {ret})"
            )

        # Step 2: Compute mapping
        ret = lib.SCOTCH_graphMapCompute(
            byref(self._graph),
            byref(mappdat),
            byref(strategy._strat),
        )

        # Step 3: Clean up mapping (always, even on error)
        lib.SCOTCH_graphMapExit(byref(self._graph), byref(mappdat))

        if ret != 0:
            raise RuntimeError(
                f"Failed to compute partition into {nparts} parts "
                f"({vertnbr} vertices) (Scotch error code: {ret})"
            )

        return parttab

    def order(
        self,
        strategy=None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute an ordering of the graph vertices (for sparse matrix factorization).

        Args:
            strategy: Ordering strategy (optional)

        Returns:
            Tuple of (permutation array, inverse permutation array)

        Raises:
            RuntimeError: If ordering fails
        """
        from .strategy import Strategy

        vertnbr, _ = self.size()

        # Create ordering arrays (dtype matches compiled Scotch)
        permtab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        peritab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        cblkptr = lib.SCOTCH_Num()

        permtab_c = permtab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        peritab_c = peritab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Use provided strategy or create default
        if strategy is None:
            strategy = Strategy()
            strategy.set_ordering_default()

        ret = lib.SCOTCH_graphOrder(
            byref(self._graph),
            byref(strategy._strat),
            permtab_c,
            peritab_c,
            byref(cblkptr),
            None,  # rangtab
            None,  # treetab
        )

        if ret != 0:
            raise RuntimeError(
                f"Failed to order graph with {vertnbr} vertices "
                f"(Scotch error code: {ret})"
            )

        return permtab, peritab

    def color(self) -> Tuple[np.ndarray, int]:
        """
        Compute a graph coloring (vertex coloring).

        Returns a coloring where no two adjacent vertices have the same color.

        Returns:
            Tuple of (color array, number of colors used)
            - color array: Array of color assignments for each vertex (0-based)
            - number of colors: Total number of colors used

        Raises:
            RuntimeError: If coloring fails
        """
        vertnbr, _ = self.size()

        # Create color array (dtype matches compiled Scotch)
        colotab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        colonbr = lib.SCOTCH_Num()

        colotab_c = colotab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        ret = lib.SCOTCH_graphColor(
            byref(self._graph),
            colotab_c,
            byref(colonbr),
            lib.SCOTCH_Num(0),  # flagval = 0
        )

        if ret != 0:
            raise RuntimeError(
                f"Failed to color graph with {vertnbr} vertices "
                f"(Scotch error code: {ret})"
            )

        return colotab, colonbr.value

    def induce_list(self, vertex_list: np.ndarray) -> "Graph":
        """
        Create an induced subgraph from a list of vertices.

        The induced subgraph contains only the specified vertices and the edges
        between them from the original graph.

        Args:
            vertex_list: Array of vertex indices to include in the subgraph

        Returns:
            New Graph instance containing the induced subgraph

        Raises:
            RuntimeError: If induction fails
        """
        indvertnbr = len(vertex_list)

        # Convert vertex list to Scotch dtype
        scotch_dtype = lib.get_scotch_dtype()
        vertex_list_scotch = vertex_list.astype(scotch_dtype)
        vertex_list_c = vertex_list_scotch.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Create new graph for induced subgraph
        induced_graph = Graph()

        ret = lib.SCOTCH_graphInduceList(
            byref(self._graph),
            lib.SCOTCH_Num(indvertnbr),
            vertex_list_c,
            byref(induced_graph._graph),
        )

        if ret != 0:
            raise RuntimeError(
                f"Failed to induce subgraph from {indvertnbr} vertices "
                f"(Scotch error code: {ret})"
            )

        return induced_graph

    def induce_part(self, partition: np.ndarray, part_id: int) -> "Graph":
        """
        Create an induced subgraph from vertices in a specific partition.

        Args:
            partition: Array of partition assignments for each vertex
            part_id: Partition ID to extract (vertices with this partition value)

        Returns:
            New Graph instance containing vertices from the specified partition

        Raises:
            RuntimeError: If induction fails
        """
        vertnbr, _ = self.size()

        # Count vertices in the requested partition
        indvertnbr = np.sum(partition == part_id)

        # Convert partition array to GraphPart2 type (unsigned char/ubyte)
        partition_ubyte = partition.astype(np.uint8)
        partition_c = partition_ubyte.ctypes.data_as(POINTER(lib.SCOTCH_GraphPart2))

        # Create new graph for induced subgraph
        induced_graph = Graph()

        ret = lib.SCOTCH_graphInducePart(
            byref(self._graph),
            lib.SCOTCH_Num(indvertnbr),
            partition_c,
            lib.SCOTCH_GraphPart2(part_id),
            byref(induced_graph._graph),
        )

        if ret != 0:
            raise RuntimeError(
                f"Failed to induce subgraph from partition {part_id} "
                f"({indvertnbr} vertices) (Scotch error code: {ret})"
            )

        return induced_graph

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

    @staticmethod
    def from_edges(
        edges: List[Tuple[int, int]],
        num_vertices: Optional[int] = None,
        vertex_weights: Optional[List[int]] = None,
        edge_weights: Optional[List[int]] = None,
    ) -> "Graph":
        """
        Create a graph from a list of edges.

        Args:
            edges: List of (source, target) tuples
            num_vertices: Number of vertices (auto-detected if None)
            vertex_weights: Optional list of vertex weights
            edge_weights: Optional list of edge weights

        Returns:
            New Graph instance

        Raises:
            ValueError: If edges list is empty or inputs are invalid
        """
        if not edges:
            raise ValueError("edges list cannot be empty")

        if num_vertices is None:
            num_vertices = max(max(e) for e in edges) + 1

        # Validate vertex indices
        max_vertex = max(max(e) for e in edges)
        if max_vertex >= num_vertices:
            raise ValueError(
                f"Edge contains vertex {max_vertex} but num_vertices is {num_vertices}"
            )

        # Validate weights if provided
        if vertex_weights is not None and len(vertex_weights) != num_vertices:
            raise ValueError(
                f"vertex_weights length ({len(vertex_weights)}) must match "
                f"num_vertices ({num_vertices})"
            )

        # Build adjacency structure
        adj = [[] for _ in range(num_vertices)]
        for i, (u, v) in enumerate(edges):
            adj[u].append(v)
            if u != v:  # Avoid duplicate for self-loops
                adj[v].append(u)

        # Create verttab and edgetab
        verttab = np.zeros(num_vertices + 1, dtype=np.int64)
        edge_count = 0
        for i, neighbors in enumerate(adj):
            verttab[i] = edge_count
            edge_count += len(neighbors)
        verttab[num_vertices] = edge_count

        edgetab = np.zeros(edge_count, dtype=np.int64)
        idx = 0
        for neighbors in adj:
            for n in neighbors:
                edgetab[idx] = n
                idx += 1

        # Create graph
        graph = Graph()

        velotab_np = np.array(vertex_weights, dtype=np.int64) if vertex_weights else None
        edlotab_np = np.array(edge_weights, dtype=np.int64) if edge_weights else None

        graph.build(verttab, edgetab, velotab_np, edlotab_np, baseval=0)

        return graph
