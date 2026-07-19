"""
High-level Graph class for PT-Scotch.
"""

import numpy as np
import ctypes
import os
from contextlib import contextmanager
from ctypes import byref, c_long, POINTER, cast, c_void_p, CDLL
from pathlib import Path
from typing import Optional, Union, List, Tuple

from .api_decorators import scotch_binding, highlevel_api, internal_api
from . import libscotch as lib


@contextmanager
def c_fopen(filename: str, mode: str = "r"):
    """
    Context manager for C FILE* pointers using our compatibility layer.

    Uses libpyscotch_compat.so which is compiled with the SAME toolchain
    as Scotch, guaranteeing perfect ABI compatibility (no struct layout
    mismatches, LFS issues, etc.)

    Args:
        filename: Path to file
        mode: File mode ("r", "w", "rb", "wb", etc.)

    Yields:
        C FILE* pointer (as ctypes.c_void_p)

    Raises:
        IOError: If file cannot be opened
        RuntimeError: If compat library cannot be loaded

    Example:
        with c_fopen("graph.grf", "r") as file_ptr:
            lib.SCOTCH_graphLoad(byref(graph._graph), file_ptr, -1, 0)
    """
    # Find the compat library in the same directory as Scotch libs.
    # lib._lib_dir is None when the system-installed Scotch is loaded: system
    # Scotch and CPython link the same platform libc, so plain fopen/fclose
    # are ABI-safe and no compat shim is needed.
    lib_dir = getattr(lib, "_lib_dir", None)
    if lib_dir is not None:
        compat_path = os.path.join(lib_dir, "libpyscotch_compat.so")
        if not os.path.exists(compat_path):
            raise RuntimeError(
                f"Compatibility library not found: {compat_path}\n"
                "Please rebuild with 'make build-all' to create libpyscotch_compat.so"
            )

        # Load our compat library (compiled with same toolchain as Scotch)
        compat = CDLL(compat_path)
        c_fopen_func = compat.pyscotch_fopen
        c_fclose_func = compat.pyscotch_fclose
        get_errno = compat.pyscotch_get_errno
        get_errno.argtypes = []
        get_errno.restype = ctypes.c_int
    else:
        libc = CDLL(None, use_errno=True)
        c_fopen_func = libc.fopen
        c_fclose_func = libc.fclose
        get_errno = ctypes.get_errno

    c_fopen_func.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    c_fopen_func.restype = ctypes.c_void_p
    c_fclose_func.argtypes = [ctypes.c_void_p]
    c_fclose_func.restype = ctypes.c_int

    # Open the file
    file_ptr = c_fopen_func(str(filename).encode(), mode.encode())

    if not file_ptr:
        errno_val = get_errno()
        raise IOError(f"Failed to open file '{filename}' with mode '{mode}' (errno: {errno_val})")

    try:
        # Yield the FILE* pointer to the caller
        yield file_ptr
    finally:
        # Always close the file
        if file_ptr:
            c_fclose_func(file_ptr)


def _coerce_edge_weights(values, what: str = "edge weights") -> Optional[np.ndarray]:
    """
    Validate edge weight values and convert them to a Scotch edge load array.

    Scotch edge loads (edlotab) must be strictly positive integers. Floating
    point values are accepted only when they are integral (e.g. 2.0).

    Args:
        values: Sequence or numpy array of edge weight values
        what: Description of the values, used in error messages

    Returns:
        numpy array with the Scotch integer dtype, or None when all weights
        equal 1 (in which case the graph should be built unweighted).

    Raises:
        ValueError: If any weight is non-numeric, non-integral, not strictly
            positive, or does not fit in the Scotch integer type.
    """
    arr = np.asarray(values)
    if arr.size == 0:
        return None
    if arr.dtype == np.bool_:
        arr = arr.astype(np.int8)
    if arr.dtype.kind == "O":
        try:
            arr = arr.astype(np.float64)
        except (TypeError, ValueError):
            raise ValueError(f"{what} must be numeric (strictly positive integers)")
    if arr.dtype.kind == "f":
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{what} must be finite (no NaN or infinity)")
        if np.any(arr != np.floor(arr)):
            raise ValueError(
                f"{what} must be integers (integral floats such as 2.0 are accepted); "
                "Scotch edge loads are integral, so scale your weights to integers first "
                "(e.g. numpy.rint(weights * scale))"
            )
    elif arr.dtype.kind not in "iu":
        raise ValueError(
            f"{what} must be numeric (strictly positive integers), got dtype {arr.dtype}"
        )
    if np.any(arr <= 0):
        raise ValueError(
            f"{what} must be strictly positive integers, found minimum value {arr.min()}. "
            "Note that explicitly stored zeros count as edges; if zero means 'no edge', "
            "remove those entries first (e.g. matrix.eliminate_zeros())"
        )
    out = arr.astype(lib.get_scotch_dtype())
    if not np.array_equal(out, arr):
        raise ValueError(
            f"{what} do not fit in the Scotch integer type ({lib.get_scotch_dtype().__name__})"
        )
    if np.all(out == 1):
        return None
    return out


@contextmanager
def _scotch_mapping(graph_ptr, arch_ptr, parttab_c):
    """Context manager for SCOTCH_graphMapInit / SCOTCH_graphMapExit."""
    mappdat = lib.SCOTCH_Mapping()
    ret = lib.SCOTCH_graphMapInit(byref(graph_ptr), byref(mappdat), byref(arch_ptr), parttab_c)
    if ret != 0:
        raise lib.scotch_error("SCOTCH_graphMapInit failed", ret)
    try:
        yield mappdat
    finally:
        lib.SCOTCH_graphMapExit(byref(graph_ptr), byref(mappdat))


@contextmanager
def _scotch_ordering(graph_ptr, permtab_c, peritab_c):
    """Context manager for SCOTCH_graphOrderInit / SCOTCH_graphOrderExit."""
    cblkptr = lib.SCOTCH_Num()
    orddat = lib.SCOTCH_Ordering()
    ret = lib.SCOTCH_graphOrderInit(
        byref(graph_ptr), byref(orddat), permtab_c, peritab_c, byref(cblkptr), None, None
    )
    if ret != 0:
        raise lib.scotch_error("SCOTCH_graphOrderInit failed", ret)
    try:
        yield orddat
    finally:
        lib.SCOTCH_graphOrderExit(byref(graph_ptr), byref(orddat))


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
        self._graph = lib.SCOTCH_Graph()
        ret = lib.SCOTCH_graphInit(byref(self._graph))
        if ret != 0:
            raise lib.scotch_error("Failed to initialize graph", ret)

        self._initialized = True
        # Keep references to arrays to prevent garbage collection
        self._verttab = None
        self._vendtab = None  # Added vendtab reference
        self._edgetab = None
        self._velotab = None
        self._edlotab = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @scotch_binding("SCOTCH_graphExit", "void SCOTCH_graphExit(SCOTCH_Graph *)")
    def close(self):
        """Release graph resources. Called automatically when used as a context manager."""
        if getattr(self, "_initialized", False):
            lib.SCOTCH_graphExit(byref(self._graph))
            self._initialized = False

    @scotch_binding(
        "SCOTCH_graphLoad", "int SCOTCH_graphLoad(SCOTCH_Graph *, FILE *, SCOTCH_Num, SCOTCH_Num)"
    )
    def load(self, filename: Union[str, Path]) -> None:
        """
        Load a graph from a file in Scotch graph format.

        Uses our C compatibility layer to avoid Python FILE* incompatibility issues.

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

        # Use our compat layer - guarantees ABI compatibility with Scotch
        # Note: baseval=0 forces 0-based indexing regardless of file content.
        # This is intentional — the Python API consistently uses 0-based indices.
        # Use -1 to preserve the file's original base value if needed.
        with c_fopen(str(filename), "r") as file_ptr:
            baseval = lib.SCOTCH_Num(0)
            ret = lib.SCOTCH_graphLoad(byref(self._graph), file_ptr, baseval, 0)

            if ret != 0:
                raise lib.scotch_error(f"Failed to load graph from {filename}", ret)

    @scotch_binding("SCOTCH_graphSave", "int SCOTCH_graphSave(const SCOTCH_Graph *, FILE *)")
    def save(self, filename: Union[str, Path]) -> None:
        """
        Save the graph to a file in Scotch graph format.

        Uses our C compatibility layer to avoid Python FILE* incompatibility issues.

        Args:
            filename: Output file path

        Raises:
            IOError: If file cannot be opened
            RuntimeError: If saving fails
        """
        filename = Path(filename)

        # Use our compat layer - guarantees ABI compatibility with Scotch
        with c_fopen(str(filename), "w") as file_ptr:
            ret = lib.SCOTCH_graphSave(byref(self._graph), file_ptr)

            if ret != 0:
                raise lib.scotch_error(f"Failed to save graph to {filename}", ret)

    @scotch_binding(
        "SCOTCH_graphBuild",
        "int SCOTCH_graphBuild(SCOTCH_Graph *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num, SCOTCH_Num *, SCOTCH_Num *)",
    )
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

        velotab_c = (
            self._velotab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
            if self._velotab is not None
            else None
        )
        edlotab_c = (
            self._edlotab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
            if self._edlotab is not None
            else None
        )

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
            raise lib.scotch_error(
                f"Failed to build graph with {vertnbr} vertices and {edgenbr} edges", ret
            )

    @scotch_binding("SCOTCH_graphCheck", "int SCOTCH_graphCheck(const SCOTCH_Graph *)")
    def check(self) -> bool:
        """
        Check the consistency of the graph structure.

        Returns:
            True if the graph is valid, False otherwise
        """
        ret = lib.SCOTCH_graphCheck(byref(self._graph))
        return ret == 0

    @scotch_binding(
        "SCOTCH_graphSize",
        "void SCOTCH_graphSize(const SCOTCH_Graph *, SCOTCH_Num *, SCOTCH_Num *)",
    )
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

    @scotch_binding("SCOTCH_graphBase", "SCOTCH_Num SCOTCH_graphBase(SCOTCH_Graph *, SCOTCH_Num)")
    def base(self, baseval: int) -> int:
        """
        Set the base value for vertex numbering.

        Args:
            baseval: New base value (0 or 1)

        Returns:
            The old base value

        Raises:
            ValueError: If baseval is invalid
        """
        if baseval not in (0, 1):
            raise ValueError(f"baseval must be 0 or 1, got {baseval}")
        old_baseval = lib.SCOTCH_graphBase(byref(self._graph), lib.SCOTCH_Num(baseval))
        return old_baseval

    @scotch_binding("SCOTCH_graphStat", "void SCOTCH_graphStat(const SCOTCH_Graph *, ...)")
    def stat(self) -> dict:
        """
        Get statistics about the graph.

        Returns:
            Dictionary with keys:
            - velomin, velomax, velosum: vertex load min/max/sum
            - degrmin, degrmax: vertex degree min/max
            - edlomin, edlomax, edlosum: edge load min/max/sum
        """
        velomin = lib.SCOTCH_Num()
        velomax = lib.SCOTCH_Num()
        velosum = lib.SCOTCH_Num()
        veloavg = ctypes.c_double()
        velodlt = ctypes.c_double()
        degrmin = lib.SCOTCH_Num()
        degrmax = lib.SCOTCH_Num()
        degravg = ctypes.c_double()
        degrdlt = ctypes.c_double()
        edlomin = lib.SCOTCH_Num()
        edlomax = lib.SCOTCH_Num()
        edlosum = lib.SCOTCH_Num()
        edloavg = ctypes.c_double()
        edlodlt = ctypes.c_double()

        lib.SCOTCH_graphStat(
            byref(self._graph),
            byref(velomin),
            byref(velomax),
            byref(velosum),
            byref(veloavg),
            byref(velodlt),
            byref(degrmin),
            byref(degrmax),
            byref(degravg),
            byref(degrdlt),
            byref(edlomin),
            byref(edlomax),
            byref(edlosum),
            byref(edloavg),
            byref(edlodlt),
        )

        return {
            "velomin": velomin.value,
            "velomax": velomax.value,
            "velosum": velosum.value,
            "degrmin": degrmin.value,
            "degrmax": degrmax.value,
            "edlomin": edlomin.value,
            "edlomax": edlomax.value,
            "edlosum": edlosum.value,
        }

    @highlevel_api(
        scotch_functions=[
            "SCOTCH_randomReset",
            "SCOTCH_graphMapInit",
            "SCOTCH_graphMapCompute",
            "SCOTCH_graphMapExit",
        ]
    )
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
            raise ValueError(f"nparts ({nparts}) cannot exceed number of vertices ({vertnbr})")

        # Create partition array (dtype matches compiled Scotch)
        parttab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        parttab_c = parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Create architecture
        arch = Architecture()
        arch.complete(nparts)

        # A fresh Strategy is Scotch's default; deferred requests (flag builds,
        # constructor strings) need nparts and are built here.
        if strategy is None:
            strategy = Strategy()
        strategy._materialize_mapping(nparts)

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
            raise lib.scotch_error(f"Failed to initialize mapping for {nparts} parts", ret)

        # Step 2: Compute mapping
        ret = lib.SCOTCH_graphMapCompute(
            byref(self._graph),
            byref(mappdat),
            byref(strategy._strat),
        )

        # Step 3: Clean up mapping (always, even on error)
        lib.SCOTCH_graphMapExit(byref(self._graph), byref(mappdat))

        if ret != 0:
            raise lib.scotch_error(
                f"Failed to compute partition into {nparts} parts ({vertnbr} vertices)", ret
            )

        return parttab

    @scotch_binding(
        "SCOTCH_graphOrder",
        "int SCOTCH_graphOrder(const SCOTCH_Graph *, const SCOTCH_Strat *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *)",
    )
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

        Note:
            Scotch's PRNG state carries across calls; for reproducible results
            call ``pyscotch.random_reset()`` before this operation.
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
        strategy._materialize_ordering()

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
            raise lib.scotch_error(f"Failed to order graph with {vertnbr} vertices", ret)

        return permtab, peritab

    @highlevel_api(scotch_functions=["SCOTCH_randomReset", "SCOTCH_graphColor"])
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
            raise lib.scotch_error(f"Failed to color graph with {vertnbr} vertices", ret)

        return colotab, colonbr.value

    @scotch_binding(
        "SCOTCH_graphInduceList",
        "int SCOTCH_graphInduceList(const SCOTCH_Graph *, SCOTCH_Num, const SCOTCH_Num *, SCOTCH_Graph *)",
    )
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
            raise lib.scotch_error(f"Failed to induce subgraph from {indvertnbr} vertices", ret)

        return induced_graph

    @scotch_binding(
        "SCOTCH_graphInducePart",
        "int SCOTCH_graphInducePart(const SCOTCH_Graph *, SCOTCH_Num, const SCOTCH_GraphPart2 *, SCOTCH_GraphPart2, SCOTCH_Graph *)",
    )
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
            raise lib.scotch_error(
                f"Failed to induce subgraph from partition {part_id} ({indvertnbr} vertices)", ret
            )

        return induced_graph

    @scotch_binding("SCOTCH_graphCoarsen", "int SCOTCH_graphCoarsen(...)")
    def coarsen(
        self,
        min_vertices: int = 1,
        coarrat: float = 0.8,
        flags: int = 0,
    ) -> Tuple[Optional["Graph"], Optional[np.ndarray]]:
        """
        Create a coarsened version of the graph.

        Args:
            min_vertices: Minimum number of coarse vertices
            coarrat: Coarsening ratio (0.0-1.0)
            flags: Coarsening flags (e.g., SCOTCH_COARSENNONE)

        Returns:
            Tuple of (coarse_graph, multinode_array) or (None, None) if
            the graph could not be coarsened.
        """
        vertnbr, _ = self.size()

        multinode = np.zeros(vertnbr * 2, dtype=lib.get_scotch_dtype())
        multinode_c = multinode.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        coarse = Graph()
        ret = lib.SCOTCH_graphCoarsen(
            byref(self._graph),
            lib.SCOTCH_Num(min_vertices),
            float(coarrat),
            lib.SCOTCH_Num(flags),
            byref(coarse._graph),
            multinode_c,
        )

        if ret == 0:
            return (coarse, multinode)
        elif ret == 1:
            return (None, None)
        else:
            raise lib.scotch_error("Failed to coarsen graph", ret)

    @scotch_binding("SCOTCH_graphCoarsenMatch", "int SCOTCH_graphCoarsenMatch(...)")
    def coarsen_match(
        self,
        coarrat: float = 0.8,
        flags: int = 0,
    ) -> Tuple[int, np.ndarray]:
        """
        Compute a matching for coarsening without building the coarse graph.

        Args:
            coarrat: Coarsening ratio
            flags: Coarsening flags

        Returns:
            Tuple of (coarse_vertex_count, mate_array)
        """
        vertnbr, _ = self.size()

        mate = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        mate_c = mate.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        coar_vertnbr = lib.SCOTCH_Num(0)

        ret = lib.SCOTCH_graphCoarsenMatch(
            byref(self._graph),
            byref(coar_vertnbr),
            float(coarrat),
            lib.SCOTCH_Num(flags),
            mate_c,
        )

        if ret != 0:
            raise lib.scotch_error("Failed to compute coarsening match", ret)

        return (coar_vertnbr.value, mate)

    @scotch_binding("SCOTCH_graphCoarsenBuild", "int SCOTCH_graphCoarsenBuild(...)")
    def coarsen_build(
        self,
        coar_vertnbr: int,
        mate: np.ndarray,
    ) -> Tuple["Graph", np.ndarray]:
        """
        Build a coarse graph from a precomputed matching.

        Args:
            coar_vertnbr: Number of coarse vertices (from coarsen_match)
            mate: Mate array (from coarsen_match)

        Returns:
            Tuple of (coarse_graph, multinode_array)
        """
        mate_arr, mate_c = lib.to_scotch_array(mate)

        multinode = np.zeros(coar_vertnbr * 2, dtype=lib.get_scotch_dtype())
        multinode_c = multinode.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        coarse = Graph()
        ret = lib.SCOTCH_graphCoarsenBuild(
            byref(self._graph),
            lib.SCOTCH_Num(coar_vertnbr),
            mate_c,
            byref(coarse._graph),
            multinode_c,
        )

        if ret != 0:
            raise lib.scotch_error("Failed to build coarse graph", ret)

        return (coarse, multinode)

    @scotch_binding("SCOTCH_graphPartFixed", "int SCOTCH_graphPartFixed(...)")
    def partition_fixed(
        self,
        nparts: int,
        parttab: np.ndarray,
        strategy=None,
    ) -> np.ndarray:
        """
        Partition the graph with some vertices fixed to specific parts.

        Args:
            nparts: Number of partitions
            parttab: Partition array. Pre-set entries (>= 0) are fixed.
                     Set to -1 for vertices that should be freely assigned.
            strategy: Partitioning strategy (optional)

        Returns:
            Updated partition array

        Note:
            Scotch's PRNG state carries across calls; for reproducible results
            call ``pyscotch.random_reset()`` before this operation.
        """
        from .strategy import Strategy

        if strategy is None:
            strategy = Strategy()
        strategy._materialize_mapping(nparts)

        parttab, parttab_c = lib.to_scotch_array(parttab, copy=True)

        ret = lib.SCOTCH_graphPartFixed(
            byref(self._graph),
            lib.SCOTCH_Num(nparts),
            byref(strategy._strat),
            parttab_c,
        )

        if ret != 0:
            raise lib.scotch_error("Failed to compute fixed partition", ret)

        return parttab

    @scotch_binding("SCOTCH_graphPartOvl", "int SCOTCH_graphPartOvl(...)")
    def partition_overlap(
        self,
        nparts: int,
        strategy=None,
    ) -> np.ndarray:
        """
        Partition the graph with overlap (vertices can belong to multiple parts).

        Args:
            nparts: Number of partitions
            strategy: Overlap partitioning strategy (optional)

        Returns:
            Partition array (values 0..nparts-1 for parts, -1 for vertices in
            the overlap, i.e. shared between several parts)

        Note:
            Scotch's PRNG state carries across calls; for reproducible results
            call ``pyscotch.random_reset()`` before this operation.
        """
        from .strategy import Strategy

        vertnbr, _ = self.size()

        parttab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        parttab_c = parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        if strategy is None:
            strategy = Strategy()
        strategy._materialize_overlap(nparts)

        ret = lib.SCOTCH_graphPartOvl(
            byref(self._graph),
            lib.SCOTCH_Num(nparts),
            byref(strategy._strat),
            parttab_c,
        )

        if ret != 0:
            raise lib.scotch_error("Failed to compute overlap partition", ret)

        return parttab

    @scotch_binding("SCOTCH_graphRepart", "int SCOTCH_graphRepart(...)")
    def repart(
        self,
        nparts: int,
        old_partition: np.ndarray,
        emrat: float = 1.0,
        vmlotab: Optional[np.ndarray] = None,
        strategy=None,
    ) -> np.ndarray:
        """
        Repartition the graph starting from an existing partition.

        Args:
            nparts: Number of partitions
            old_partition: Previous partition to improve upon
            emrat: Edge migration ratio (higher = more migration allowed)
            vmlotab: Vertex migration cost array (optional)
            strategy: Repartitioning strategy (optional)

        Returns:
            New partition array

        Note:
            Scotch's PRNG state carries across calls; for reproducible results
            call ``pyscotch.random_reset()`` before this operation.
        """
        from .strategy import Strategy

        vertnbr, _ = self.size()

        if strategy is None:
            strategy = Strategy()
        strategy._materialize_mapping(nparts)

        old_part, old_part_c = lib.to_scotch_array(old_partition, copy=True)

        parttab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        parttab_c = parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        vmlotab_arr, vmlotab_c = lib.to_scotch_array_optional(vmlotab)

        ret = lib.SCOTCH_graphRepart(
            byref(self._graph),
            lib.SCOTCH_Num(nparts),
            old_part_c,
            float(emrat),
            vmlotab_c,
            byref(strategy._strat),
            parttab_c,
        )

        if ret != 0:
            raise lib.scotch_error("Failed to repartition graph", ret)

        return parttab

    @scotch_binding("SCOTCH_graphMapSave", "int SCOTCH_graphMapSave(...)")
    def map_save(self, filename: Union[str, Path], parttab: np.ndarray, arch) -> None:
        """
        Save a mapping to a file in Scotch mapping format.

        Args:
            filename: Output file path
            parttab: Partition/mapping array
            arch: Architecture the mapping targets
        """
        parttab_arr, parttab_c = lib.to_scotch_array(parttab)
        with _scotch_mapping(self._graph, arch._arch, parttab_c) as mappdat:
            with c_fopen(str(filename), "w") as fp:
                ret = lib.SCOTCH_graphMapSave(byref(self._graph), byref(mappdat), fp)
                if ret != 0:
                    raise lib.scotch_error("Failed to save mapping", ret)

    @scotch_binding("SCOTCH_graphMapView", "int SCOTCH_graphMapView(...)")
    def map_view(self, filename: Union[str, Path], parttab: np.ndarray, arch) -> None:
        """
        Save mapping statistics to a file.

        Args:
            filename: Output file path
            parttab: Partition/mapping array
            arch: Architecture the mapping targets
        """
        parttab_arr, parttab_c = lib.to_scotch_array(parttab)
        with _scotch_mapping(self._graph, arch._arch, parttab_c) as mappdat:
            with c_fopen(str(filename), "w") as fp:
                ret = lib.SCOTCH_graphMapView(byref(self._graph), byref(mappdat), fp)
                if ret != 0:
                    raise lib.scotch_error("Failed to write mapping view", ret)

    @scotch_binding("SCOTCH_graphOrderCheck", "int SCOTCH_graphOrderCheck(...)")
    def order_check(self, permtab: np.ndarray, peritab: np.ndarray) -> bool:
        """
        Check the validity of an ordering.

        Args:
            permtab: Forward permutation array
            peritab: Inverse permutation array

        Returns:
            True if ordering is valid
        """
        permtab_arr, permtab_c = lib.to_scotch_array(permtab)
        peritab_arr, peritab_c = lib.to_scotch_array(peritab)
        with _scotch_ordering(self._graph, permtab_c, peritab_c) as orddat:
            ret = lib.SCOTCH_graphOrderCheck(byref(self._graph), byref(orddat))
            return ret == 0

    @scotch_binding("SCOTCH_graphOrderSave", "int SCOTCH_graphOrderSave(...)")
    def order_save(
        self, filename: Union[str, Path], permtab: np.ndarray, peritab: np.ndarray
    ) -> None:
        """
        Save an ordering to a file in Scotch ordering format.

        Args:
            filename: Output file path
            permtab: Forward permutation array
            peritab: Inverse permutation array
        """
        permtab_arr, permtab_c = lib.to_scotch_array(permtab)
        peritab_arr, peritab_c = lib.to_scotch_array(peritab)
        with _scotch_ordering(self._graph, permtab_c, peritab_c) as orddat:
            with c_fopen(str(filename), "w") as fp:
                ret = lib.SCOTCH_graphOrderSave(byref(self._graph), byref(orddat), fp)
                if ret != 0:
                    raise lib.scotch_error("Failed to save ordering", ret)

    @scotch_binding("SCOTCH_graphTabSave", "int SCOTCH_graphTabSave(...)")
    def tab_save(self, filename: Union[str, Path], tab: np.ndarray) -> None:
        """
        Save a partition/mapping table to a file.

        Args:
            filename: Output file path
            tab: Array to save (one value per vertex)
        """
        tab_arr, tab_c = lib.to_scotch_array(tab)
        with c_fopen(str(filename), "w") as fp:
            ret = lib.SCOTCH_graphTabSave(byref(self._graph), tab_c, fp)
            if ret != 0:
                raise lib.scotch_error("Failed to save tab", ret)

    @scotch_binding("SCOTCH_graphTabLoad", "int SCOTCH_graphTabLoad(...)")
    def tab_load(self, filename: Union[str, Path]) -> np.ndarray:
        """
        Load a partition/mapping table from a file.

        Args:
            filename: Input file path

        Returns:
            Array of values (one per vertex)
        """
        vertnbr, _ = self.size()
        tab = np.zeros(vertnbr, dtype=lib.get_scotch_dtype())
        tab_c = tab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        with c_fopen(str(filename), "r") as fp:
            ret = lib.SCOTCH_graphTabLoad(byref(self._graph), tab_c, fp)
            if ret != 0:
                raise lib.scotch_error("Failed to load tab", ret)

        return tab

    @internal_api
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
    @highlevel_api(scotch_functions=["SCOTCH_graphInit", "SCOTCH_graphBuild"])
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

        # Create verttab and edgetab using the correct dtype for the loaded Scotch variant
        scotch_dtype = lib.get_scotch_dtype()
        verttab = np.zeros(num_vertices + 1, dtype=scotch_dtype)
        edge_count = 0
        for i, neighbors in enumerate(adj):
            verttab[i] = edge_count
            edge_count += len(neighbors)
        verttab[num_vertices] = edge_count

        edgetab = np.zeros(edge_count, dtype=scotch_dtype)
        idx = 0
        for neighbors in adj:
            for n in neighbors:
                edgetab[idx] = n
                idx += 1

        # Create graph
        graph = Graph()

        velotab_np = np.array(vertex_weights, dtype=scotch_dtype) if vertex_weights else None
        edlotab_np = np.array(edge_weights, dtype=scotch_dtype) if edge_weights else None

        graph.build(verttab, edgetab, velotab_np, edlotab_np, baseval=0)

        return graph

    @internal_api
    def _csr_arrays(self) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        """
        Extract the graph adjacency as normalized (0-based, compact) CSR arrays.

        Uses SCOTCH_graphData to access Scotch's internal arrays and copies
        them into fresh numpy arrays, re-basing indices to 0 and compacting
        the edge array if the internal representation is not compact.

        Returns:
            Tuple of (indptr, indices, edlotab) where edlotab is None when
            the graph carries no edge loads. indptr has vertnbr + 1 entries;
            indices and edlotab have one entry per arc (each undirected edge
            appears twice, once per direction).
        """
        scotch_dtype = lib.get_scotch_dtype()

        baseval = lib.SCOTCH_Num()
        vertnbr = lib.SCOTCH_Num()
        edgenbr = lib.SCOTCH_Num()
        verttab_p = POINTER(lib.SCOTCH_Num)()
        vendtab_p = POINTER(lib.SCOTCH_Num)()
        velotab_p = POINTER(lib.SCOTCH_Num)()
        vlbltab_p = POINTER(lib.SCOTCH_Num)()
        edgetab_p = POINTER(lib.SCOTCH_Num)()
        edlotab_p = POINTER(lib.SCOTCH_Num)()

        lib.SCOTCH_graphData(
            byref(self._graph),
            byref(baseval),
            byref(vertnbr),
            byref(verttab_p),
            byref(vendtab_p),
            byref(velotab_p),
            byref(vlbltab_p),
            byref(edgenbr),
            byref(edgetab_p),
            byref(edlotab_p),
        )

        base = baseval.value
        n = vertnbr.value
        if n <= 0:
            return (np.zeros(1, dtype=scotch_dtype), np.zeros(0, dtype=scotch_dtype), None)

        # verttab/vendtab point at the first vertex; copy them out of Scotch memory
        verttab = np.ctypeslib.as_array(verttab_p, shape=(n,)).astype(scotch_dtype)
        vendtab = np.ctypeslib.as_array(vendtab_p, shape=(n,)).astype(scotch_dtype)

        indptr = np.zeros(n + 1, dtype=scotch_dtype)
        np.cumsum(vendtab - verttab, out=indptr[1:])
        arcnbr = int(indptr[-1])

        if arcnbr == 0:
            return (indptr, np.zeros(0, dtype=scotch_dtype), None)

        # Arcs of vertex i live at edgetab[verttab[i]-base : vendtab[i]-base]
        buflen = int(vendtab.max()) - base
        edgebuf = np.ctypeslib.as_array(edgetab_p, shape=(buflen,))
        edlobuf = np.ctypeslib.as_array(edlotab_p, shape=(buflen,)) if bool(edlotab_p) else None

        compact = verttab[0] == base and (n == 1 or np.array_equal(verttab[1:], vendtab[:-1]))
        if compact:
            sel = slice(0, arcnbr)
        else:
            sel = np.concatenate(
                [np.arange(int(verttab[i]) - base, int(vendtab[i]) - base) for i in range(n)]
            )
        indices = edgebuf[sel].astype(scotch_dtype) - base
        edlotab = edlobuf[sel].astype(scotch_dtype) if edlobuf is not None else None

        return (indptr, indices, edlotab)

    @classmethod
    @highlevel_api(scotch_functions=["SCOTCH_graphInit", "SCOTCH_graphBuild"])
    def from_scipy_sparse(
        cls,
        matrix,
        *,
        use_edge_weights: bool = True,
        drop_self_loops: bool = False,
    ) -> "Graph":
        """
        Create a graph from a scipy sparse adjacency matrix.

        Accepts any scipy sparse matrix or array (CSR, CSC, COO, LIL, ...);
        the input is converted to canonical CSR form (duplicate entries are
        summed). Scotch graphs are undirected, so the matrix must be square
        and symmetric in both structure and values.

        Requires scipy (install with the ``interop`` extra:
        ``uv pip install pyscotch[interop]``).

        Args:
            matrix: scipy sparse adjacency matrix/array. Entry (i, j) means an
                edge between vertices i and j; it must equal entry (j, i).
            use_edge_weights: If True (default) and the stored values are not
                all 1, they are used as Scotch edge loads and must be strictly
                positive integers (integral floats such as 2.0 are accepted).
                If False, values are ignored: explicitly stored zeros are
                dropped and every remaining entry becomes an unweighted edge.
            drop_self_loops: If True, stored diagonal entries (self-loops) are
                silently removed. If False (default), a ValueError is raised
                when the diagonal has stored entries.

        Returns:
            New Graph instance (vertex i of the graph corresponds to row i)

        Raises:
            TypeError: If matrix is not a scipy sparse matrix/array
            ValueError: If the matrix is not square, not symmetric (fix with
                ``A = A + A.T`` or ``A = A.maximum(A.T)``), has self-loops
                (unless drop_self_loops=True), or has invalid edge weights

        Example:
            >>> import numpy as np
            >>> import scipy.sparse as sp
            >>> A = sp.csr_array(np.array([[0, 2, 0], [2, 0, 3], [0, 3, 0]]))
            >>> graph = Graph.from_scipy_sparse(A)
            >>> graph.size()
            (3, 4)
            >>> parts = graph.partition(2)  # parts[i] is the part of row i
        """
        from scipy import sparse  # Lazy import: scipy is an optional dependency

        if not sparse.issparse(matrix):
            raise TypeError(
                f"from_scipy_sparse expects a scipy sparse matrix/array, got {type(matrix).__name__}. "
                "For dense arrays, wrap them first, e.g. scipy.sparse.csr_array(dense)"
            )
        nrow, ncol = matrix.shape
        if nrow != ncol:
            raise ValueError(f"adjacency matrix must be square, got shape {matrix.shape}")
        if nrow == 0:
            raise ValueError("cannot build a Scotch graph from an empty (0x0) matrix")

        # Canonical CSR copy (never mutate the caller's matrix)
        A = matrix.tocsr(copy=True)
        A.sum_duplicates()
        A.sort_indices()
        if A.dtype == np.bool_:
            A = A.astype(np.int8)

        if not use_edge_weights:
            # Values are ignored: apply scipy semantics (stored zero = no edge)
            # and binarize so the symmetry check below is structure-only.
            A.eliminate_zeros()
            A.data[...] = 1

        # Self-loops: any stored diagonal entry
        row_of_entry = np.repeat(np.arange(nrow), np.diff(A.indptr))
        loop_mask = A.indices == row_of_entry
        if loop_mask.any():
            if not drop_self_loops:
                raise ValueError(
                    f"adjacency matrix has {int(loop_mask.sum())} stored diagonal entries "
                    "(self-loops); Scotch graphs cannot contain self-loops. "
                    "Pass drop_self_loops=True to remove them"
                )
            keep = ~loop_mask
            counts = np.bincount(row_of_entry[keep], minlength=nrow)
            indptr = np.zeros(nrow + 1, dtype=A.indptr.dtype)
            np.cumsum(counts, out=indptr[1:])
            A = sparse.csr_matrix((A.data[keep], A.indices[keep], indptr), shape=A.shape)

        # Scotch graphs are undirected: structure AND values must be symmetric
        if (A != A.T).nnz != 0:
            raise ValueError(
                "adjacency matrix must be symmetric in both structure and values "
                "(Scotch graphs are undirected). Symmetrize it first, e.g. with "
                "A = A + A.T, or A = A.maximum(A.T) to keep existing weights unchanged"
            )

        edlotab = (
            _coerce_edge_weights(A.data, what="edge weights (matrix values)")
            if use_edge_weights
            else None
        )

        scotch_dtype = lib.get_scotch_dtype()
        graph = cls()
        graph.build(
            A.indptr.astype(scotch_dtype),
            A.indices.astype(scotch_dtype),
            edlotab=edlotab,
            baseval=0,
        )
        return graph

    @highlevel_api(scotch_functions=["SCOTCH_graphData"])
    def to_scipy_sparse(self):
        """
        Export the graph adjacency as a scipy sparse CSR matrix.

        The result is a square CSR matrix whose entry (i, j) is the load of
        the edge between vertices i and j (1 for unweighted graphs, 0 when
        there is no edge). Since Scotch graphs are undirected, the result is
        always symmetric. Round-trip is exact:
        ``Graph.from_scipy_sparse(A).to_scipy_sparse()`` has the same
        structure and values as A.

        Requires scipy (install with the ``interop`` extra).

        Returns:
            scipy.sparse.csr_array (csr_matrix on very old scipy) with integer
            index arrays and integer data (edge loads, or 1s if unweighted)

        Example:
            >>> graph = Graph.from_edges([(0, 1), (1, 2), (2, 0)], num_vertices=3)
            >>> A = graph.to_scipy_sparse()
            >>> A.shape, A.nnz
            ((3, 3), 6)
        """
        from scipy import sparse  # Lazy import: scipy is an optional dependency

        indptr, indices, edlotab = self._csr_arrays()
        n = len(indptr) - 1
        data = edlotab if edlotab is not None else np.ones(len(indices), dtype=indices.dtype)
        csr_type = sparse.csr_array if hasattr(sparse, "csr_array") else sparse.csr_matrix
        return csr_type((data, indices, indptr), shape=(n, n))

    @classmethod
    @highlevel_api(scotch_functions=["SCOTCH_graphInit", "SCOTCH_graphBuild"])
    def from_networkx(cls, G, *, weight: str = "weight") -> Tuple["Graph", list]:
        """
        Create a graph from a networkx undirected simple graph.

        Node labels may be arbitrary hashable objects; Scotch vertices are
        numbered 0..n-1 following ``list(G.nodes())``. The returned ``nodes``
        list maps Scotch vertex indices back to networkx labels: ``nodes[i]``
        is the label of Scotch vertex i. Keep it to interpret result arrays,
        e.g. ``parts = graph.partition(4)`` assigns node ``nodes[i]`` to part
        ``parts[i]``.

        Requires networkx (install with the ``interop`` extra:
        ``uv pip install pyscotch[interop]``).

        Args:
            G: networkx undirected simple graph (nx.Graph). Directed graphs
                and multigraphs are rejected; convert them first.
            weight: Name of the edge attribute holding edge weights (default
                "weight"). If at least one edge carries the attribute, weights
                are used as Scotch edge loads and must be strictly positive
                integers (integral floats accepted); edges missing the
                attribute default to 1. If no edge has the attribute, or if
                all weights equal 1, the graph is built unweighted.
                Pass weight=None to ignore edge weights entirely.

        Returns:
            Tuple of (graph, nodes) where nodes[i] is the networkx label of
            Scotch vertex i

        Raises:
            TypeError: If G is directed (convert with ``G.to_undirected()``),
                a multigraph (convert with ``nx.Graph(G)``), or not a
                networkx graph at all
            ValueError: If G is empty, has self-loops (remove with
                ``G.remove_edges_from(nx.selfloop_edges(G))``), or has
                invalid edge weights

        Example:
            >>> import networkx as nx
            >>> G = nx.Graph([("a", "b"), ("b", "c")])
            >>> graph, nodes = Graph.from_networkx(G)
            >>> parts = graph.partition(2)
            >>> {nodes[i]: int(parts[i]) for i in range(len(nodes))}  # doctest: +SKIP
            {'a': 0, 'b': 0, 'c': 1}
        """
        import networkx as nx  # Lazy import: networkx is an optional dependency

        if not (hasattr(G, "is_directed") and hasattr(G, "is_multigraph") and hasattr(G, "adj")):
            raise TypeError(f"from_networkx expects a networkx graph, got {type(G).__name__}")
        if G.is_directed():
            raise TypeError(
                "from_networkx only accepts undirected simple graphs (nx.Graph), got a directed "
                "graph; Scotch graphs are undirected. Convert it first, e.g. "
                "Graph.from_networkx(G.to_undirected())"
            )
        if G.is_multigraph():
            raise TypeError(
                "from_networkx only accepts undirected simple graphs (nx.Graph), got a multigraph. "
                "Collapse parallel edges first, e.g. Graph.from_networkx(nx.Graph(G))"
            )
        if G.number_of_nodes() == 0:
            raise ValueError("cannot build a Scotch graph from an empty networkx graph")
        loopnbr = nx.number_of_selfloops(G)
        if loopnbr != 0:
            raise ValueError(
                f"graph has {loopnbr} self-loop(s); Scotch graphs cannot contain self-loops. "
                "Remove them first: G.remove_edges_from(nx.selfloop_edges(G))"
            )

        nodes = list(G.nodes())
        index = {node: i for i, node in enumerate(nodes)}

        use_weights = weight is not None and any(weight in d for _, _, d in G.edges(data=True))

        indptr = [0]
        indices = []
        loads = [] if use_weights else None
        for u in nodes:
            for v, attrs in G.adj[u].items():
                indices.append(index[v])
                if use_weights:
                    loads.append(attrs.get(weight, 1))
            indptr.append(len(indices))

        edlotab = None
        if use_weights:
            edlotab = _coerce_edge_weights(loads, what=f"edge weights (attribute {weight!r})")

        scotch_dtype = lib.get_scotch_dtype()
        graph = cls()
        graph.build(
            np.asarray(indptr, dtype=scotch_dtype),
            np.asarray(indices, dtype=scotch_dtype),
            edlotab=edlotab,
            baseval=0,
        )
        return graph, nodes

    @highlevel_api(scotch_functions=["SCOTCH_graphData"])
    def to_networkx(self, *, nodes: Optional[list] = None):
        """
        Export the graph as a networkx undirected graph.

        Requires networkx (install with the ``interop`` extra).

        Args:
            nodes: Optional list of node labels, one per vertex, where
                nodes[i] is the label of Scotch vertex i (typically the list
                returned by from_networkx). Defaults to integer labels 0..n-1.

        Returns:
            nx.Graph with one node per vertex and one edge per undirected
            edge. If the graph carries edge loads, each edge gets a "weight"
            attribute (int); unweighted graphs produce edges without a
            "weight" attribute.

        Raises:
            ValueError: If nodes is given and its length does not match the
                number of vertices

        Example:
            >>> graph = Graph.from_edges([(0, 1), (1, 2)], num_vertices=3)
            >>> H = graph.to_networkx(nodes=["a", "b", "c"])
            >>> sorted(H.edges())
            [('a', 'b'), ('b', 'c')]
        """
        import networkx as nx  # Lazy import: networkx is an optional dependency

        indptr, indices, edlotab = self._csr_arrays()
        n = len(indptr) - 1

        if nodes is not None:
            nodes = list(nodes)
            if len(nodes) != n:
                raise ValueError(f"nodes has {len(nodes)} labels but the graph has {n} vertices")
        else:
            nodes = list(range(n))

        G = nx.Graph()
        G.add_nodes_from(nodes)
        for i in range(n):
            for k in range(int(indptr[i]), int(indptr[i + 1])):
                j = int(indices[k])
                if i > j:
                    continue  # Each undirected edge appears as two arcs; add it once
                if edlotab is not None:
                    G.add_edge(nodes[i], nodes[j], weight=int(edlotab[k]))
                else:
                    G.add_edge(nodes[i], nodes[j])
        return G
