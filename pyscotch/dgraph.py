"""
Distributed Graph (PT-Scotch) API.

This module provides a Pythonic interface to PT-Scotch's distributed graph
operations, which use MPI for parallel processing.
"""

import numpy as np
from contextlib import contextmanager
from pathlib import Path
import ctypes
from ctypes import byref, POINTER, c_int
from typing import Optional, Tuple

from pyscotch.libscotch import (
    SCOTCH_COARSENNONE as COARSEN_NONE,
    SCOTCH_COARSENFOLD as COARSEN_FOLD,
    SCOTCH_COARSENFOLDDUP as COARSEN_FOLDDUP,
    SCOTCH_COARSENNOMERGE as COARSEN_NOMERGE,
    SCOTCH_DGRAPHBUILDGRID3DGRID as GRID3D_GRID,
    SCOTCH_DGRAPHBUILDGRID3DTORUS as GRID3D_TORUS,
    SCOTCH_DGRAPHBUILDGRID3DNGB6 as GRID3D_NGB6,
    SCOTCH_DGRAPHBUILDGRID3DNGB26 as GRID3D_NGB26,
    SCOTCH_DGRAPHBUILDGRID3DVERTLOAD as GRID3D_VERTLOAD,
    SCOTCH_DGRAPHBUILDGRID3DEDGELOAD as GRID3D_EDGELOAD,
)
from pyscotch import libscotch as lib
from pyscotch.api_decorators import scotch_binding, highlevel_api, internal_api
from pyscotch.mpi import mpi
from pyscotch.graph import c_fopen


def _resolve_comm(comm):
    """Resolve a Dgraph ``comm`` argument to what Scotch and Python each need.

    Accepts three forms and returns ``(scotch_comm, mpi4py_comm)`` where
    ``scotch_comm`` is a ``ctypes.c_void_p`` holding the native ``MPI_Comm``
    value to pass to ``SCOTCH_dgraphInit`` (by value), and ``mpi4py_comm`` is
    the original mpi4py communicator object (or ``None``) so rank-dependent
    methods can query it directly:

    - ``None``: use the bundled zero-dependency MPI wrapper's ``MPI_COMM_WORLD``.
      Requires ``mpi.init()`` to have been called first.
    - an **mpi4py** communicator (``mpi4py.MPI.Comm``): its native ``MPI_Comm``
      handle is extracted with ``MPI._handleof`` — verified to be the exact same
      value the bundled wrapper derives for ``MPI_COMM_WORLD``. mpi4py runs
      ``MPI_Init`` itself on import, so no ``mpi.init()`` is needed.
    - a raw ``ctypes.c_void_p`` (or ``int``) ``MPI_Comm`` handle: passed through
      unchanged (escape hatch; also how ``coarsen`` reuses a parent's comm).
    """
    if comm is None:
        if not mpi.is_initialized():
            raise RuntimeError(
                "MPI must be initialized before creating Dgraph.\n"
                "Call mpi.init() first, or pass an mpi4py communicator "
                "(e.g. Dgraph(comm=MPI.COMM_WORLD))."
            )
        return mpi.get_comm_world(), None

    if isinstance(comm, ctypes.c_void_p):
        return comm, None
    if isinstance(comm, int):
        return ctypes.c_void_p(comm), None

    # Anything else may only be an mpi4py communicator. Gate on the module name
    # BEFORE importing mpi4py, so a stray object never triggers mpi4py's import
    # side effect (MPI_Init) just to be type-checked.
    if type(comm).__module__.split(".", 1)[0] == "mpi4py":
        from mpi4py import MPI

        if isinstance(comm, MPI.Comm):
            return ctypes.c_void_p(MPI._handleof(comm)), comm

    raise TypeError(
        "Dgraph comm must be None, an mpi4py communicator, or a ctypes "
        f"c_void_p MPI_Comm handle, not {type(comm).__name__}."
    )


class Dgraph:
    """
    Distributed graph for PT-Scotch parallel partitioning and ordering.

    A distributed graph (Dgraph) represents a graph that is partitioned across
    multiple MPI processes. Each process holds a portion of the vertices and edges.

    This requires:
    - PT-Scotch library loaded (parallel variant)
    - MPI initialized
    - Running in an MPI environment (e.g., via mpirun/mpiexec)

    Example (mpi4py — recommended when you already use MPI from Python):
        >>> # export PYSCOTCH_INT_SIZE=64
        >>> # export PYSCOTCH_PARALLEL=1
        >>> from mpi4py import MPI            # runs MPI_Init on import
        >>> from pyscotch import Dgraph
        >>>
        >>> dgraph = Dgraph(comm=MPI.COMM_WORLD)   # any sub-communicator works too
        >>> dgraph.build_grid_3d(8, 8, 8)          # each rank gets its share
        >>> part = dgraph.part(4)                  # local part assignments
        >>> dgraph.exit()
        >>> # Run with:  mpirun -n 4 python script.py

    Example (bundled zero-dependency wrapper, no mpi4py):
        >>> from pyscotch import mpi, Dgraph
        >>> mpi.init()
        >>> dgraph = Dgraph()                      # bundled MPI_COMM_WORLD
        >>> dgraph.build(vertloctab, edgeloctab, baseval=0)
        >>> dgraph.exit()
        >>> mpi.finalize()
    """

    def __init__(self, comm=None):
        """
        Initialize a distributed graph.

        Args:
            comm: MPI communicator (default: MPI_COMM_WORLD via the bundled
                  zero-dependency MPI wrapper, after mpi.init()). Accepts:
                  - None: bundled wrapper's MPI_COMM_WORLD (requires mpi.init());
                  - an mpi4py communicator, e.g. ``Dgraph(comm=MPI.COMM_WORLD)``
                    or any sub-communicator — the recommended path when you use
                    mpi4py (no mpi.init() needed);
                  - a ctypes.c_void_p (or int) raw MPI_Comm handle.

        Raises:
            RuntimeError: If PT-Scotch (parallel variant) is not loaded
            RuntimeError: If comm is None and MPI is not initialized
            TypeError: If comm is an unsupported type
        """
        # Check that parallel variant is loaded
        if not lib.is_parallel():
            raise RuntimeError(
                "Dgraph requires PT-Scotch (parallel variant).\n"
                "Set PYSCOTCH_PARALLEL=1 environment variable before importing pyscotch."
            )

        # Resolve the communicator: `_comm` is the native MPI_Comm handle to
        # hand Scotch (also reused by coarsen); `_mpi4py_comm` is the mpi4py
        # object, if any, so rank queries can go straight through it.
        self._comm, self._mpi4py_comm = _resolve_comm(comm)

        # Initialize distributed graph
        self._dgraph = lib.SCOTCH_Dgraph()
        self._exit_called = False
        ret = lib.SCOTCH_dgraphInit(byref(self._dgraph), self._comm)
        if ret != 0:
            raise lib.scotch_error("SCOTCH_dgraphInit failed", ret)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()
        return False

    @scotch_binding("SCOTCH_dgraphExit", "void SCOTCH_dgraphExit(SCOTCH_Dgraph *)")
    def exit(self):
        """Release distributed graph resources.

        Call this before MPI finalize to ensure proper cleanup.
        Also called automatically when used as a context manager.
        """
        if hasattr(self, "_dgraph") and not self._exit_called:
            lib.SCOTCH_dgraphExit(byref(self._dgraph))
            self._exit_called = True

    @scotch_binding(
        "SCOTCH_dgraphBuild",
        "int SCOTCH_dgraphBuild(SCOTCH_Dgraph *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *)",
    )
    def build(
        self,
        vertloctab: np.ndarray,
        edgeloctab: np.ndarray,
        baseval: int = 0,
        vendloctab: Optional[np.ndarray] = None,
        veloloctab: Optional[np.ndarray] = None,
        vlblloctab: Optional[np.ndarray] = None,
        edgegsttab: Optional[np.ndarray] = None,
        edloloctab: Optional[np.ndarray] = None,
    ) -> None:
        """
        Build the distributed graph from local data on this MPI process.

        Each MPI process calls this with its local portion of the graph.

        Args:
            vertloctab: Local vertex array (CSR format).
                        Length = vertlocnbr + 1, contains edge indices.
            edgeloctab: Local edge array (neighbor vertex indices).
                        Length = edgelocnbr.
            baseval: Base value for indexing (0 or 1).
            vendloctab: Optional end indices for vertices (default: vertloctab[1:]).
            veloloctab: Optional vertex weights/loads.
            vlblloctab: Optional vertex labels.
            edgegsttab: Optional ghost edge array (for edges to remote vertices).
            edloloctab: Optional edge weights/loads.

        Note:
            The distributed graph uses CSR format like sequential graphs, but
            each process only holds its local portion. Ghost vertices/edges
            may reference vertices on other processes.
        """
        # Ensure correct dtype
        vertloctab, vertloctab_c = lib.to_scotch_array(vertloctab)
        edgeloctab, edgeloctab_c = lib.to_scotch_array(edgeloctab)

        # Calculate sizes
        vertlocnbr = len(vertloctab) - 1  # Number of local vertices
        vertlocmax = vertlocnbr  # Maximum local vertex index
        edgelocnbr = len(edgeloctab)  # Number of local edges
        edgelocsiz = edgelocnbr  # Size of edge array

        # Handle optional arrays
        vendloctab, vendloctab_ptr = lib.to_scotch_array_optional(vendloctab)
        veloloctab, veloloctab_ptr = lib.to_scotch_array_optional(veloloctab)
        vlblloctab, vlblloctab_ptr = lib.to_scotch_array_optional(vlblloctab)
        edgegsttab, edgegsttab_ptr = lib.to_scotch_array_optional(edgegsttab)
        edloloctab, edloloctab_ptr = lib.to_scotch_array_optional(edloloctab)

        # Build the distributed graph
        ret = lib.SCOTCH_dgraphBuild(
            byref(self._dgraph),
            lib.SCOTCH_Num(baseval),
            lib.SCOTCH_Num(vertlocnbr),
            lib.SCOTCH_Num(vertlocmax),
            vertloctab_c,
            vendloctab_ptr,
            veloloctab_ptr,
            vlblloctab_ptr,
            lib.SCOTCH_Num(edgelocnbr),
            lib.SCOTCH_Num(edgelocsiz),
            edgeloctab_c,
            edgegsttab_ptr,
            edloloctab_ptr,
        )

        if ret != 0:
            raise lib.scotch_error("SCOTCH_dgraphBuild failed", ret)

    @scotch_binding("SCOTCH_dgraphCheck", "int SCOTCH_dgraphCheck(const SCOTCH_Dgraph *)")
    def check(self) -> bool:
        """
        Check the consistency of the distributed graph.

        This performs various sanity checks on the graph structure across
        all MPI processes.

        Returns:
            True if the graph is consistent, False otherwise.
        """
        ret = lib.SCOTCH_dgraphCheck(byref(self._dgraph))
        return ret == 0

    @scotch_binding(
        "SCOTCH_dgraphLoad",
        "int SCOTCH_dgraphLoad(SCOTCH_Dgraph *, FILE *, SCOTCH_Num, SCOTCH_Num)",
    )
    def load(self, filepath: Path, baseval: int = 0, flagval: int = 0) -> None:
        """
        Load a distributed graph from a file.

        The file is read by the root process (rank 0) and distributed to all processes.

        Args:
            filepath: Path to the graph file.
            baseval: Base value for indexing (0 or 1, or -1 for auto-detect).
            flagval: Loading flags.

        Raises:
            RuntimeError: If loading fails.
        """
        filepath = Path(filepath)

        # Only process 0 opens the file, others pass NULL
        rank = self._comm_rank()

        if rank == 0:
            with c_fopen(filepath, "r") as file_ptr:
                ret = lib.SCOTCH_dgraphLoad(
                    byref(self._dgraph),
                    file_ptr,
                    lib.SCOTCH_Num(baseval),
                    lib.SCOTCH_Num(flagval),
                )
        else:
            # Non-root processes pass NULL file pointer
            ret = lib.SCOTCH_dgraphLoad(
                byref(self._dgraph),
                None,
                lib.SCOTCH_Num(baseval),
                lib.SCOTCH_Num(flagval),
            )

        if ret != 0:
            raise lib.scotch_error(f"Failed to load distributed graph from {filepath}", ret)

    @scotch_binding("SCOTCH_dgraphSave", "int SCOTCH_dgraphSave(SCOTCH_Dgraph *, FILE *)")
    def save(self, filepath: Path) -> None:
        """
        Save the distributed graph to a file.

        The graph is gathered to the root process and saved.

        Args:
            filepath: Path where the graph should be saved.

        Raises:
            RuntimeError: If saving fails.
        """
        filepath = Path(filepath)

        with c_fopen(filepath, "w") as file_ptr:
            ret = lib.SCOTCH_dgraphSave(byref(self._dgraph), file_ptr)

        if ret != 0:
            raise lib.scotch_error(f"Failed to save distributed graph to {filepath}", ret)

    @scotch_binding("SCOTCH_dgraphData", "void SCOTCH_dgraphData(...)")
    def data(
        self,
        want_baseval: bool = False,
        want_vertglbnbr: bool = False,
        want_vertlocnbr: bool = False,
        want_vertlocmax: bool = False,
        want_vertgstnbr: bool = False,
        want_vertloctab: bool = False,
        want_vendloctab: bool = False,
        want_veloloctab: bool = False,
        want_vlblloctab: bool = False,
        want_edgeglbnbr: bool = False,
        want_edgelocnbr: bool = False,
        want_edgelocsiz: bool = False,
        want_edgeloctab: bool = False,
        want_edgegsttab: bool = False,
        want_edloloctab: bool = False,
        want_commptr: bool = False,
    ):
        """
        Get selected internal data fields from the distributed graph.

        This method follows Scotch's design philosophy of selective field retrieval.
        Pass NULL (via False) for unwanted fields to avoid accessing potentially
        invalid data (e.g., on folded ranks after coarsening).

        Args:
            want_baseval: Get base value for indexing
            want_vertglbnbr: Get global number of vertices
            want_vertlocnbr: Get local number of vertices
            want_vertlocmax: Get maximum local vertices
            want_vertgstnbr: Get number of local + ghost vertices
            want_vertloctab: Get vertex array pointer
            want_vendloctab: Get vertex end array pointer
            want_veloloctab: Get vertex weights pointer
            want_vlblloctab: Get vertex labels pointer
            want_edgeglbnbr: Get global number of edges
            want_edgelocnbr: Get local number of edges
            want_edgelocsiz: Get size of edge array
            want_edgeloctab: Get edge array pointer
            want_edgegsttab: Get ghost edge array pointer
            want_edloloctab: Get edge weights pointer
            want_commptr: Get MPI communicator

        Returns:
            Dictionary containing only the requested fields.

        Note:
            Array pointers reference internal Scotch data.
            Do not modify them or use after the graph is destroyed.

        Example:
            >>> # Only get vertex counts (safe on all ranks)
            >>> data = dgraph.data(want_vertglbnbr=True, want_vertlocnbr=True)
            >>> print(data['vertglbnbr'], data['vertlocnbr'])
        """
        # Conditionally create variables for requested fields
        baseval = lib.SCOTCH_Num() if want_baseval else None
        vertglbnbr = lib.SCOTCH_Num() if want_vertglbnbr else None
        vertlocnbr = lib.SCOTCH_Num() if want_vertlocnbr else None
        vertlocmax = lib.SCOTCH_Num() if want_vertlocmax else None
        vertgstnbr = lib.SCOTCH_Num() if want_vertgstnbr else None
        vertloctab = POINTER(lib.SCOTCH_Num)() if want_vertloctab else None
        vendloctab = POINTER(lib.SCOTCH_Num)() if want_vendloctab else None
        veloloctab = POINTER(lib.SCOTCH_Num)() if want_veloloctab else None
        vlblloctab = POINTER(lib.SCOTCH_Num)() if want_vlblloctab else None
        edgeglbnbr = lib.SCOTCH_Num() if want_edgeglbnbr else None
        edgelocnbr = lib.SCOTCH_Num() if want_edgelocnbr else None
        edgelocsiz = lib.SCOTCH_Num() if want_edgelocsiz else None
        edgeloctab = POINTER(lib.SCOTCH_Num)() if want_edgeloctab else None
        edgegsttab = POINTER(lib.SCOTCH_Num)() if want_edgegsttab else None
        edloloctab = POINTER(lib.SCOTCH_Num)() if want_edloloctab else None
        # MPI_Comm is written here by value: 8-byte pointer under OpenMPI,
        # 4-byte int under MPICH — c_void_p is large enough for both
        commptr = ctypes.c_void_p() if want_commptr else None

        # Call SCOTCH_dgraphData with NULL for unwanted fields
        lib.SCOTCH_dgraphData(
            byref(self._dgraph),
            byref(baseval) if baseval is not None else None,
            byref(vertglbnbr) if vertglbnbr is not None else None,
            byref(vertlocnbr) if vertlocnbr is not None else None,
            byref(vertlocmax) if vertlocmax is not None else None,
            byref(vertgstnbr) if vertgstnbr is not None else None,
            byref(vertloctab) if vertloctab is not None else None,
            byref(vendloctab) if vendloctab is not None else None,
            byref(veloloctab) if veloloctab is not None else None,
            byref(vlblloctab) if vlblloctab is not None else None,
            byref(edgeglbnbr) if edgeglbnbr is not None else None,
            byref(edgelocnbr) if edgelocnbr is not None else None,
            byref(edgelocsiz) if edgelocsiz is not None else None,
            byref(edgeloctab) if edgeloctab is not None else None,
            byref(edgegsttab) if edgegsttab is not None else None,
            byref(edloloctab) if edloloctab is not None else None,
            byref(commptr) if commptr is not None else None,
        )

        # Build result dict with only requested fields
        result = {}
        if want_baseval:
            result["baseval"] = baseval.value
        if want_vertglbnbr:
            result["vertglbnbr"] = vertglbnbr.value
        if want_vertlocnbr:
            result["vertlocnbr"] = vertlocnbr.value
        if want_vertlocmax:
            result["vertlocmax"] = vertlocmax.value
        if want_vertgstnbr:
            result["vertgstnbr"] = vertgstnbr.value
        if want_vertloctab:
            result["vertloctab"] = vertloctab
        if want_vendloctab:
            result["vendloctab"] = vendloctab
        if want_veloloctab:
            result["veloloctab"] = veloloctab
        if want_vlblloctab:
            result["vlblloctab"] = vlblloctab
        if want_edgeglbnbr:
            result["edgeglbnbr"] = edgeglbnbr.value
        if want_edgelocnbr:
            result["edgelocnbr"] = edgelocnbr.value
        if want_edgelocsiz:
            result["edgelocsiz"] = edgelocsiz.value
        if want_edgeloctab:
            result["edgeloctab"] = edgeloctab
        if want_edgegsttab:
            result["edgegsttab"] = edgegsttab
        if want_edloloctab:
            result["edloloctab"] = edloloctab
        if want_commptr:
            result["commptr"] = commptr.value

        return result

    @scotch_binding(
        "SCOTCH_dgraphCoarsenVertLocMax",
        "SCOTCH_Num SCOTCH_dgraphCoarsenVertLocMax(const SCOTCH_Dgraph *, SCOTCH_Num)",
    )
    def coarsen_vert_loc_max(self, foldval: int = COARSEN_NONE) -> int:
        """
        Get maximum size needed for multinode array in coarsening.

        Args:
            foldval: Coarsening mode (COARSEN_NONE, COARSEN_FOLD, etc.)

        Returns:
            Maximum number of local vertices in coarsened graph

        Example:
            >>> max_size = dgraph.coarsen_vert_loc_max(COARSEN_FOLD)
            >>> multloctab = np.zeros(max_size * 2, dtype=np.int64)
        """
        result = lib.SCOTCH_dgraphCoarsenVertLocMax(byref(self._dgraph), lib.SCOTCH_Num(foldval))
        return int(result)

    @highlevel_api(
        scotch_functions=[
            "SCOTCH_dgraphInit",
            "SCOTCH_dgraphCoarsenVertLocMax",
            "SCOTCH_dgraphCoarsen",
        ]
    )
    def coarsen(
        self, coarrat: float = 0.8, foldval: int = COARSEN_NONE, flags: int = 0
    ) -> tuple["Dgraph", Optional[np.ndarray]]:
        """
        Create a coarsened version of this distributed graph.

        Coarsening merges similar vertices to create a smaller graph, used in
        multilevel algorithms for partitioning and ordering.

        Args:
            coarrat: Coarsening ratio (0.0-1.0). Higher values = more aggressive.
                     Default: 0.8 (lazy coarsening)
            foldval: Coarsening mode:
                     - COARSEN_NONE: Plain coarsening (all processes active)
                     - COARSEN_FOLD: Folding (reduces number of processes)
                     - COARSEN_FOLDDUP: Folding with duplication
                     Default: COARSEN_NONE
            flags: Additional flags (currently unused, pass 0)

        Returns:
            Tuple of (coarse_graph, multinode_array):
            - coarse_graph: New Dgraph containing coarsened graph
            - multinode_array: Maps fine vertices to coarse vertices (or None)
                              Shape: (coarvertlocmax * 2,) if graph was coarsened

        Raises:
            RuntimeError: If coarsening fails

        Note:
            - Returns (coarse_graph, None) if graph could not be coarsened
              (not considered an error - graph may be too small)
            - With COARSEN_FOLD, some processes may not have a coarse graph
              (folding reduces active processes)

        Example:
            >>> coarse, multloctab = dgraph.coarsen(0.8, COARSEN_NONE)
            >>> if multloctab is not None:
            ...     print(f"Coarsened to {coarse.data()['vertlocnbr']} vertices")
        """
        # Get maximum size for multinode array
        coarvertlocmax = self.coarsen_vert_loc_max(foldval)

        # Allocate multinode array
        multloctab = np.zeros(coarvertlocmax * 2, dtype=lib.get_scotch_dtype())

        # Create coarse graph on the same communicator (pass the mpi4py object
        # through when we have one, so the child keeps rank queries mpi4py-based)
        coarse_graph = Dgraph(
            comm=self._mpi4py_comm if self._mpi4py_comm is not None else self._comm
        )

        # Perform coarsening
        ret = lib.SCOTCH_dgraphCoarsen(
            byref(self._dgraph),
            lib.SCOTCH_Num(flags),
            float(coarrat),
            lib.SCOTCH_Num(foldval),
            byref(coarse_graph._dgraph),
            multloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
        )

        if ret == 0:
            # Success - graph was coarsened
            return (coarse_graph, multloctab)
        elif ret == 1:
            # Graph could not be coarsened (not an error)
            # This can happen if graph is too small or already optimal
            # IMPORTANT: The coarse graph is in an INVALID state when ret == 1.
            # We must NOT call SCOTCH_dgraphExit on it (per Scotch semantics),
            # so mark it as already exited to prevent __del__ from cleaning up.
            coarse_graph._exit_called = True
            return (coarse_graph, None)
        else:
            # Error — coarse graph is also invalid
            coarse_graph._exit_called = True
            raise lib.scotch_error("Failed to coarsen graph", ret)

    @scotch_binding("SCOTCH_dgraphGhst", "int SCOTCH_dgraphGhst(SCOTCH_Dgraph *)")
    def ghst(self) -> int:
        """
        Compute ghost edge array for distributed graph.

        Ghost edges are edges that connect local vertices to remote vertices.
        This operation builds internal data structures needed for operations
        like grow() that need to know about neighboring processes.

        Returns:
            0 on success

        Raises:
            RuntimeError: If ghost edge computation fails

        Note:
            - This is required before calling grow()
            - Modifies the graph in-place by adding ghost edge information

        Example:
            >>> dgraph.ghst()
            >>> # Now dgraph has ghost edge information for grow()
        """
        ret = lib.SCOTCH_dgraphGhst(byref(self._dgraph))
        if ret != 0:
            raise lib.scotch_error("Failed to compute ghost edge array", ret)
        return ret

    @scotch_binding(
        "SCOTCH_dgraphGrow",
        "int SCOTCH_dgraphGrow(SCOTCH_Dgraph *, SCOTCH_Num, SCOTCH_Num *, SCOTCH_Num, SCOTCH_Num *)",
    )
    def grow(
        self, seedlocnbr: int, seedloctab: np.ndarray, distmax: int, partgsttab: np.ndarray
    ) -> int:
        """
        Grow subgraphs from seed vertices to create partitions.

        Starting from seed vertices, grows regions by including neighboring
        vertices up to a maximum distance. Used for adaptive mesh refinement
        and region growing.

        Args:
            seedlocnbr: Number of seed vertices on this process
            seedloctab: Array of seed vertex indices (local numbering)
            distmax: Maximum distance to grow from seeds
            partgsttab: Partition array (includes ghost vertices!)
                       Modified in-place. Must be initialized with seed
                       partition IDs before calling.
                       Size: vertgstnbr (NOT vertlocnbr!)

        Returns:
            0 on success

        Raises:
            RuntimeError: If grow operation fails

        Note:
            - Must call ghst() before calling this method
            - partgsttab must be sized for ghost vertices (vertgstnbr)
            - Seeds must be marked in partgsttab before calling

        Example:
            >>> dgraph.ghst()
            >>> seedloctab = np.array([baseval, baseval+1], dtype=np.int64)
            >>> partgsttab = np.full(vertgstnbr, -1, dtype=np.int64)
            >>> partgsttab[0] = 0  # Mark first seed as partition 0
            >>> partgsttab[1] = 1  # Mark second seed as partition 1
            >>> dgraph.grow(2, seedloctab, 4, partgsttab)
        """
        ret = lib.SCOTCH_dgraphGrow(
            byref(self._dgraph),
            lib.SCOTCH_Num(seedlocnbr),
            seedloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            lib.SCOTCH_Num(distmax),
            partgsttab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to grow graph", ret)
        return ret

    @scotch_binding(
        "SCOTCH_dgraphBand",
        "int SCOTCH_dgraphBand(SCOTCH_Dgraph *, SCOTCH_Num, SCOTCH_Num *, SCOTCH_Num, SCOTCH_Dgraph *)",
    )
    def band(
        self, fronlocnbr: int, fronloctab: np.ndarray, distmax: int, bandgrafdat: "Dgraph"
    ) -> int:
        """
        Extract a band graph containing vertices within distance from frontier.

        Creates a subgraph containing all vertices within a maximum distance
        from a set of frontier vertices. Used for sparse matrix reordering
        and domain decomposition.

        Args:
            fronlocnbr: Number of frontier vertices on this process
            fronloctab: Array of frontier vertex indices (local numbering)
            distmax: Maximum distance from frontier to include
            bandgrafdat: Output band graph (must be initialized)

        Returns:
            0 on success

        Raises:
            RuntimeError: If band extraction fails

        Note:
            - Band graph will have vertex labels (vlblloctab)
            - Vertices in band graph reference original graph indices

        Example:
            >>> fronloctab = np.array([baseval], dtype=np.int64)
            >>> fronlocnbr = 1 if rank == 1 else 0  # Only rank 1 has frontier
            >>> bandgrafdat = Dgraph()
            >>> dgraph.band(fronlocnbr, fronloctab, 4, bandgrafdat)
            >>> # bandgrafdat now contains vertices within distance 4 of frontier
        """
        ret = lib.SCOTCH_dgraphBand(
            byref(self._dgraph),
            lib.SCOTCH_Num(fronlocnbr),
            fronloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            lib.SCOTCH_Num(distmax),
            byref(bandgrafdat._dgraph),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to compute band graph", ret)
        return ret

    @scotch_binding(
        "SCOTCH_dgraphRedist",
        "int SCOTCH_dgraphRedist(SCOTCH_Dgraph *, const SCOTCH_Num *, const SCOTCH_Num *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Dgraph *)",
    )
    def redist(
        self,
        partloctab: np.ndarray,
        permgsttab: Optional[np.ndarray] = None,
        vertlocdlt: int = -1,
        edgelocdlt: int = -1,
        dstgrafdat: "Dgraph" = None,
    ) -> int:
        """
        Redistribute graph across processes according to partition.

        Moves vertices between processes based on a partition assignment.
        Used for dynamic load balancing and repartitioning.

        Args:
            partloctab: Target partition for each local vertex
            permgsttab: Optional redistribution permutation array (None = auto)
            vertlocdlt: Extra size for local vertex array (-1 = no extra, clamped to 0)
            edgelocdlt: Extra size for local edge array (-1 = no extra, clamped to 0)
            dstgrafdat: Output redistributed graph (must be initialized)

        Returns:
            0 on success

        Raises:
            RuntimeError: If redistribution fails

        Note:
            - Vertices move between processes based on partloctab values
            - Negative vertlocdlt/edgelocdlt values are clamped to 0 by Scotch

        Example:
            >>> # Create partition: packs of 3 vertices, round-robin across processes
            >>> partloctab = np.zeros(vertlocnbr, dtype=np.int64)
            >>> for i in range(vertlocnbr):
            ...     partloctab[i] = (i // 3) % size
            >>> dstgrafdat = Dgraph()
            >>> srcgrafdat.redist(partloctab, dstgrafdat=dstgrafdat)
        """
        # Handle None permgsttab by passing NULL pointer
        permgsttab_ptr = (
            None if permgsttab is None else permgsttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )

        ret = lib.SCOTCH_dgraphRedist(
            byref(self._dgraph),
            partloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            permgsttab_ptr,
            lib.SCOTCH_Num(vertlocdlt),
            lib.SCOTCH_Num(edgelocdlt),
            byref(dstgrafdat._dgraph),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to redistribute graph", ret)
        return ret

    @scotch_binding(
        "SCOTCH_dgraphInducePart",
        "int SCOTCH_dgraphInducePart(SCOTCH_Dgraph *, const SCOTCH_Num *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Dgraph *)",
    )
    def induce_part(
        self, orgpartloctab: np.ndarray, partval: int, indvertlocnbr: int, indgrafdat: "Dgraph"
    ) -> int:
        """
        Extract induced subgraph for vertices in a specific partition.

        Creates a subgraph containing only vertices that belong to a specific
        partition value. Used for hierarchical partitioning and recursive
        bisection.

        Args:
            orgpartloctab: Partition array (which partition each vertex belongs to)
            partval: Which partition to extract (e.g., 1)
            indvertlocnbr: Number of vertices in this partition on local process
            indgrafdat: Output induced subgraph (must be initialized)

        Returns:
            0 on success

        Raises:
            RuntimeError: If induced subgraph extraction fails

        Note:
            - Induced graph has different vertex numbering than original
            - Only vertices with orgpartloctab[i] == partval are included

        Example:
            >>> # Create partition: half vertices in part 1, half in part 0
            >>> orgpartloctab = np.zeros(orgvertlocnbr, dtype=np.int64)
            >>> indvertlocnbr = (orgvertlocnbr + 1) // 2
            >>> for i in range(indvertlocnbr):
            ...     orgpartloctab[shuffled_indices[i]] = 1
            >>> indgrafdat = Dgraph()
            >>> orggrafdat.induce_part(orgpartloctab, 1, indvertlocnbr, indgrafdat)
        """
        ret = lib.SCOTCH_dgraphInducePart(
            byref(self._dgraph),
            orgpartloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            lib.SCOTCH_Num(partval),
            lib.SCOTCH_Num(indvertlocnbr),
            byref(indgrafdat._dgraph),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to induce subgraph", ret)
        return ret

    # =========================================================================
    # Structure management
    # =========================================================================

    @scotch_binding("SCOTCH_dgraphFree", "void SCOTCH_dgraphFree(SCOTCH_Dgraph *)")
    def free(self) -> None:
        """
        Free the graph contents while keeping the structure initialized.

        Unlike exit(), the Dgraph remains usable afterwards (e.g. for a new
        build() or load()), like a freshly initialized structure.
        """
        lib.SCOTCH_dgraphFree(byref(self._dgraph))

    @scotch_binding(
        "SCOTCH_dgraphBuildGrid3D",
        "int SCOTCH_dgraphBuildGrid3D(SCOTCH_Dgraph *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num)",
    )
    def build_grid_3d(
        self,
        dimx: int,
        dimy: int,
        dimz: int,
        baseval: int = 0,
        incrval: int = 1,
        flagval: int = GRID3D_GRID | GRID3D_NGB6,
    ) -> None:
        """
        Build a distributed 3D grid/torus graph.

        Each MPI process receives its share of the dimx*dimy*dimz vertices.
        Useful for testing and benchmarking without input files.

        Args:
            dimx, dimy, dimz: Grid dimensions (all >= 1)
            baseval: Base value for indexing (0 or 1)
            incrval: Distribution increment (>= 1); 1 means contiguous blocks,
                     higher values stride vertices across processes
            flagval: Bitwise-or of GRID3D_* flags (GRID3D_TORUS for wraparound
                     edges, GRID3D_NGB26 for 26-neighbor connectivity,
                     GRID3D_VERTLOAD / GRID3D_EDGELOAD for synthetic loads)

        Raises:
            RuntimeError: If building fails
        """
        ret = lib.SCOTCH_dgraphBuildGrid3D(
            byref(self._dgraph),
            lib.SCOTCH_Num(baseval),
            lib.SCOTCH_Num(dimx),
            lib.SCOTCH_Num(dimy),
            lib.SCOTCH_Num(dimz),
            lib.SCOTCH_Num(incrval),
            lib.SCOTCH_Num(flagval),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to build 3D grid distributed graph", ret)

    @scotch_binding("SCOTCH_dgraphStat", "int SCOTCH_dgraphStat(const SCOTCH_Dgraph *, ...)")
    def stat(self) -> dict:
        """
        Get global statistics about the distributed graph (collective call).

        Returns:
            Dictionary with keys:
            - velomin, velomax, velosum, veloavg, velodlt: vertex loads
            - degrmin, degrmax, degravg, degrdlt: vertex degrees
            - edlomin, edlomax, edlosum, edloavg, edlodlt: edge loads
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

        ret = lib.SCOTCH_dgraphStat(
            byref(self._dgraph),
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
        if ret != 0:
            raise lib.scotch_error("Failed to compute distributed graph statistics", ret)

        return {
            "velomin": velomin.value,
            "velomax": velomax.value,
            "velosum": velosum.value,
            "veloavg": veloavg.value,
            "velodlt": velodlt.value,
            "degrmin": degrmin.value,
            "degrmax": degrmax.value,
            "degravg": degravg.value,
            "degrdlt": degrdlt.value,
            "edlomin": edlomin.value,
            "edlomax": edlomax.value,
            "edlosum": edlosum.value,
            "edloavg": edloavg.value,
            "edlodlt": edlodlt.value,
        }

    # =========================================================================
    # Centralized <-> distributed conversion
    # =========================================================================

    @scotch_binding(
        "SCOTCH_dgraphGather", "int SCOTCH_dgraphGather(const SCOTCH_Dgraph *, SCOTCH_Graph *)"
    )
    def gather(self, graph=None):
        """
        Gather the distributed graph into a centralized (sequential) Graph.

        Collective call. Exactly one process (single root) — or every process
        (allgather) — must pass a Graph; the others pass None.

        Args:
            graph: Initialized pyscotch.Graph to receive the centralized graph
                   on this process, or None if this process is not a root.

        Returns:
            The Graph that was passed in (or None).

        Raises:
            RuntimeError: If gathering fails

        Example:
            >>> cgraph = Graph() if rank == 0 else None
            >>> dgraph.gather(cgraph)
        """
        graph_ptr = byref(graph._graph) if graph is not None else None
        ret = lib.SCOTCH_dgraphGather(byref(self._dgraph), graph_ptr)
        if ret != 0:
            raise lib.scotch_error("Failed to gather distributed graph", ret)
        return graph

    @scotch_binding(
        "SCOTCH_dgraphScatter", "int SCOTCH_dgraphScatter(SCOTCH_Dgraph *, const SCOTCH_Graph *)"
    )
    def scatter(self, graph=None) -> None:
        """
        Scatter a centralized (sequential) Graph into this distributed graph.

        Collective call. Exactly one process passes the source Graph; all
        other processes pass None.

        Args:
            graph: pyscotch.Graph holding the graph to distribute (root
                   process only), or None on non-root processes.

        Raises:
            RuntimeError: If scattering fails

        Example:
            >>> cgraph = Graph() if rank == 0 else None
            >>> if cgraph:
            ...     cgraph.load("graph.grf")
            >>> dgraph.scatter(cgraph)
        """
        graph_ptr = byref(graph._graph) if graph is not None else None
        ret = lib.SCOTCH_dgraphScatter(byref(self._dgraph), graph_ptr)
        if ret != 0:
            raise lib.scotch_error("Failed to scatter graph to distributed graph", ret)

    # =========================================================================
    # Distributed partitioning and mapping
    # =========================================================================

    @internal_api
    def _vertlocnbr(self) -> int:
        """Number of local vertices on this process."""
        return self.data(want_vertlocnbr=True)["vertlocnbr"]

    @internal_api
    def _comm_rank(self) -> int:
        """Rank of this process in the graph's communicator.

        Prefers the mpi4py communicator when the Dgraph was created from one,
        so no ``mpi.init()`` on the bundled wrapper is required.
        """
        if self._mpi4py_comm is not None:
            return self._mpi4py_comm.Get_rank()
        return mpi.comm_rank(self._comm)

    @internal_api
    @contextmanager
    def _root_fopen(self, filepath, mode: str):
        """Open a file on the root process of this graph's communicator only.

        PT-Scotch save routines are collective but expect a non-NULL stream
        on exactly one process; all others must pass NULL.
        """
        if self._comm_rank() == 0:
            with c_fopen(Path(filepath), mode) as file_ptr:
                yield file_ptr
        else:
            yield None

    @internal_api
    @contextmanager
    def _scotch_dmapping(self, arch, partloctab_c):
        """Context manager for SCOTCH_dgraphMapInit / SCOTCH_dgraphMapExit."""
        dmapdat = lib.SCOTCH_Dmapping()
        ret = lib.SCOTCH_dgraphMapInit(
            byref(self._dgraph), byref(dmapdat), byref(arch._arch), partloctab_c
        )
        if ret != 0:
            raise lib.scotch_error("SCOTCH_dgraphMapInit failed", ret)
        try:
            yield dmapdat
        finally:
            lib.SCOTCH_dgraphMapExit(byref(self._dgraph), byref(dmapdat))

    @scotch_binding(
        "SCOTCH_dgraphPart",
        "int SCOTCH_dgraphPart(SCOTCH_Dgraph *, SCOTCH_Num, SCOTCH_Strat *, SCOTCH_Num *)",
    )
    def part(self, nparts: int, strategy=None) -> np.ndarray:
        """
        Partition the distributed graph into a specified number of parts.

        Collective call: every process receives the part assignments of its
        local vertices. Behaves like the sequential Graph.partition().

        Args:
            nparts: Number of partitions
            strategy: Parallel mapping Strategy (optional; default lets
                      PT-Scotch pick its built-in default strategy)

        Returns:
            Array of part assignments for the local vertices (length
            vertlocnbr, values in [0, nparts))

        Raises:
            ValueError: If nparts is invalid
            RuntimeError: If partitioning fails
        """
        if nparts < 1:
            raise ValueError(f"nparts must be at least 1, got {nparts}")

        from pyscotch.strategy import Strategy

        if strategy is None:
            strategy = Strategy()

        partloctab = np.zeros(self._vertlocnbr(), dtype=lib.get_scotch_dtype())

        ret = lib.SCOTCH_dgraphPart(
            byref(self._dgraph),
            lib.SCOTCH_Num(nparts),
            byref(strategy._strat),
            partloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
        )
        if ret != 0:
            raise lib.scotch_error(
                f"Failed to partition distributed graph into {nparts} parts", ret
            )

        return partloctab

    @scotch_binding(
        "SCOTCH_dgraphMap",
        "int SCOTCH_dgraphMap(SCOTCH_Dgraph *, const SCOTCH_Arch *, SCOTCH_Strat *, SCOTCH_Num *)",
    )
    def map(self, arch, strategy=None) -> np.ndarray:
        """
        Map the distributed graph onto a target architecture.

        Collective call: every process receives the target domains of its
        local vertices.

        Args:
            arch: Target Architecture
            strategy: Parallel mapping Strategy (optional)

        Returns:
            Array of target domain assignments for the local vertices

        Raises:
            RuntimeError: If mapping fails
        """
        from pyscotch.strategy import Strategy

        if strategy is None:
            strategy = Strategy()

        partloctab = np.zeros(self._vertlocnbr(), dtype=lib.get_scotch_dtype())

        ret = lib.SCOTCH_dgraphMap(
            byref(self._dgraph),
            byref(arch._arch),
            byref(strategy._strat),
            partloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to map distributed graph", ret)

        return partloctab

    @highlevel_api(
        scotch_functions=[
            "SCOTCH_dgraphMapInit",
            "SCOTCH_dgraphMapCompute",
            "SCOTCH_dgraphMapExit",
        ]
    )
    def map_compute(self, arch, strategy=None) -> np.ndarray:
        """
        Map the distributed graph using the 3-step Init/Compute/Exit API.

        Same result as map(), but goes through the explicit distributed
        mapping structure (SCOTCH_Dmapping).

        Args:
            arch: Target Architecture
            strategy: Parallel mapping Strategy (optional)

        Returns:
            Array of target domain assignments for the local vertices
        """
        from pyscotch.strategy import Strategy

        if strategy is None:
            strategy = Strategy()

        partloctab = np.zeros(self._vertlocnbr(), dtype=lib.get_scotch_dtype())
        partloctab_c = partloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        with self._scotch_dmapping(arch, partloctab_c) as dmapdat:
            ret = lib.SCOTCH_dgraphMapCompute(
                byref(self._dgraph), byref(dmapdat), byref(strategy._strat)
            )
            if ret != 0:
                raise lib.scotch_error("Failed to compute distributed mapping", ret)

        return partloctab

    @scotch_binding(
        "SCOTCH_dgraphMapSave",
        "int SCOTCH_dgraphMapSave(const SCOTCH_Dgraph *, const SCOTCH_Dmapping *, FILE *)",
    )
    def map_save(self, filepath, arch, strategy=None) -> np.ndarray:
        """
        Compute a mapping onto arch and save it to a file (root process).

        Collective call. The mapping is computed with the distributed mapping
        structure, then written by the root process of the communicator.

        Args:
            filepath: Output file path (written on the root process)
            arch: Target Architecture
            strategy: Parallel mapping Strategy (optional)

        Returns:
            Array of target domain assignments for the local vertices
        """
        from pyscotch.strategy import Strategy

        if strategy is None:
            strategy = Strategy()

        partloctab = np.zeros(self._vertlocnbr(), dtype=lib.get_scotch_dtype())
        partloctab_c = partloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        with self._scotch_dmapping(arch, partloctab_c) as dmapdat:
            ret = lib.SCOTCH_dgraphMapCompute(
                byref(self._dgraph), byref(dmapdat), byref(strategy._strat)
            )
            if ret != 0:
                raise lib.scotch_error("Failed to compute distributed mapping", ret)
            with self._root_fopen(filepath, "w") as file_ptr:
                ret = lib.SCOTCH_dgraphMapSave(byref(self._dgraph), byref(dmapdat), file_ptr)
            if ret != 0:
                raise lib.scotch_error(f"Failed to save distributed mapping to {filepath}", ret)

        return partloctab

    @scotch_binding(
        "SCOTCH_dgraphMapView",
        "int SCOTCH_dgraphMapView(SCOTCH_Dgraph *, const SCOTCH_Dmapping *, FILE *)",
    )
    def map_view(self, filepath, arch, strategy=None) -> np.ndarray:
        """
        Compute a mapping onto arch and write its statistics to a file.

        Collective call; the statistics are written by the root process.

        Args:
            filepath: Output file path (written on the root process)
            arch: Target Architecture
            strategy: Parallel mapping Strategy (optional)

        Returns:
            Array of target domain assignments for the local vertices
        """
        from pyscotch.strategy import Strategy

        if strategy is None:
            strategy = Strategy()

        partloctab = np.zeros(self._vertlocnbr(), dtype=lib.get_scotch_dtype())
        partloctab_c = partloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        with self._scotch_dmapping(arch, partloctab_c) as dmapdat:
            ret = lib.SCOTCH_dgraphMapCompute(
                byref(self._dgraph), byref(dmapdat), byref(strategy._strat)
            )
            if ret != 0:
                raise lib.scotch_error("Failed to compute distributed mapping", ret)
            with self._root_fopen(filepath, "w") as file_ptr:
                ret = lib.SCOTCH_dgraphMapView(byref(self._dgraph), byref(dmapdat), file_ptr)
            if ret != 0:
                raise lib.scotch_error(
                    f"Failed to write distributed mapping view to {filepath}", ret
                )

        return partloctab

    # =========================================================================
    # Distributed ordering
    # =========================================================================

    @scotch_binding(
        "SCOTCH_dgraphOrderInit",
        "int SCOTCH_dgraphOrderInit(const SCOTCH_Dgraph *, SCOTCH_Dordering *)",
    )
    def order_init(self):
        """
        Initialize a distributed ordering structure for this graph.

        Returns:
            An opaque SCOTCH_Dordering handle to pass to the other order_*
            methods. Release it with order_exit() once done.

        Raises:
            RuntimeError: If initialization fails
        """
        dordering = lib.SCOTCH_Dordering()
        ret = lib.SCOTCH_dgraphOrderInit(byref(self._dgraph), byref(dordering))
        if ret != 0:
            raise lib.scotch_error("SCOTCH_dgraphOrderInit failed", ret)
        return dordering

    @scotch_binding(
        "SCOTCH_dgraphOrderExit",
        "void SCOTCH_dgraphOrderExit(const SCOTCH_Dgraph *, SCOTCH_Dordering *)",
    )
    def order_exit(self, dordering) -> None:
        """Release a distributed ordering structure created by order_init()."""
        lib.SCOTCH_dgraphOrderExit(byref(self._dgraph), byref(dordering))

    @scotch_binding(
        "SCOTCH_dgraphOrderCompute",
        "int SCOTCH_dgraphOrderCompute(SCOTCH_Dgraph *, SCOTCH_Dordering *, SCOTCH_Strat *)",
    )
    def order_compute(self, dordering, strategy=None) -> None:
        """
        Compute a distributed ordering of the graph (collective call).

        Args:
            dordering: Handle from order_init()
            strategy: Parallel ordering Strategy (optional; default lets
                      PT-Scotch pick its built-in default strategy)

        Raises:
            RuntimeError: If the ordering computation fails
        """
        from pyscotch.strategy import Strategy

        if strategy is None:
            strategy = Strategy()

        ret = lib.SCOTCH_dgraphOrderCompute(
            byref(self._dgraph), byref(dordering), byref(strategy._strat)
        )
        if ret != 0:
            raise lib.scotch_error("Failed to compute distributed ordering", ret)

    @scotch_binding(
        "SCOTCH_dgraphOrderComputeList",
        "int SCOTCH_dgraphOrderComputeList(SCOTCH_Dgraph *, SCOTCH_Dordering *, SCOTCH_Num, const SCOTCH_Num *, SCOTCH_Strat *)",
    )
    def order_compute_list(
        self,
        dordering,
        listloctab: Optional[np.ndarray],
        strategy=None,
    ) -> None:
        """
        Compute a distributed ordering of a subset of the graph vertices.

        Only the listed local vertices are ordered (first); the other
        vertices are ordered afterwards. Collective call.

        Args:
            dordering: Handle from order_init()
            listloctab: Array of based local vertex indices to order, or None
                        for an empty list (no vertex of this process is
                        specifically ordered)
            strategy: Parallel ordering Strategy (optional)

        Raises:
            RuntimeError: If the ordering computation fails
        """
        from pyscotch.strategy import Strategy

        if strategy is None:
            strategy = Strategy()

        if listloctab is None:
            listlocnbr = 0
            listloctab_c = None
        else:
            listloctab, listloctab_c = lib.to_scotch_array(listloctab)
            listlocnbr = len(listloctab)

        ret = lib.SCOTCH_dgraphOrderComputeList(
            byref(self._dgraph),
            byref(dordering),
            lib.SCOTCH_Num(listlocnbr),
            listloctab_c,
            byref(strategy._strat),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to compute distributed ordering of vertex list", ret)

    @scotch_binding(
        "SCOTCH_dgraphOrderPerm",
        "int SCOTCH_dgraphOrderPerm(const SCOTCH_Dgraph *, const SCOTCH_Dordering *, SCOTCH_Num *)",
    )
    def order_perm(self, dordering) -> np.ndarray:
        """
        Get the direct permutation of a computed distributed ordering.

        Returns:
            Array of length vertlocnbr: the new (global) indices of the
            local vertices of this process.

        Raises:
            RuntimeError: If retrieving the permutation fails
        """
        permloctab = np.zeros(self._vertlocnbr(), dtype=lib.get_scotch_dtype())
        ret = lib.SCOTCH_dgraphOrderPerm(
            byref(self._dgraph),
            byref(dordering),
            permloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to get distributed ordering permutation", ret)
        return permloctab

    @scotch_binding(
        "SCOTCH_dgraphOrderCblkDist",
        "SCOTCH_Num SCOTCH_dgraphOrderCblkDist(const SCOTCH_Dgraph *, const SCOTCH_Dordering *)",
    )
    def order_cblk_dist(self, dordering) -> int:
        """
        Get the number of distributed elimination-tree column blocks.

        Returns:
            Number of distributed column blocks of the ordering

        Raises:
            RuntimeError: If the number cannot be retrieved
        """
        result = int(lib.SCOTCH_dgraphOrderCblkDist(byref(self._dgraph), byref(dordering)))
        if result < 0:
            raise lib.scotch_error("Failed to get distributed column block count")
        return result

    @scotch_binding(
        "SCOTCH_dgraphOrderTreeDist",
        "int SCOTCH_dgraphOrderTreeDist(const SCOTCH_Dgraph *, const SCOTCH_Dordering *, SCOTCH_Num *, SCOTCH_Num *)",
    )
    def order_tree_dist(self, dordering) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get the distributed part of the elimination tree structure.

        Returns:
            Tuple of (treeglbtab, sizeglbtab), both of length
            order_cblk_dist(): the father index and size of each distributed
            column block.

        Raises:
            RuntimeError: If the tree structure cannot be retrieved
        """
        cblkglbnbr = self.order_cblk_dist(dordering)
        treeglbtab = np.zeros(cblkglbnbr, dtype=lib.get_scotch_dtype())
        sizeglbtab = np.zeros(cblkglbnbr, dtype=lib.get_scotch_dtype())
        ret = lib.SCOTCH_dgraphOrderTreeDist(
            byref(self._dgraph),
            byref(dordering),
            treeglbtab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            sizeglbtab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to get distributed elimination tree", ret)
        return treeglbtab, sizeglbtab

    @scotch_binding(
        "SCOTCH_dgraphOrderSave",
        "int SCOTCH_dgraphOrderSave(const SCOTCH_Dgraph *, const SCOTCH_Dordering *, FILE *)",
    )
    def order_save(self, dordering, filepath) -> None:
        """
        Save a distributed ordering to a file (root process).

        Collective call; the ordering is gathered and written by the root
        process of the communicator.
        """
        with self._root_fopen(filepath, "w") as file_ptr:
            ret = lib.SCOTCH_dgraphOrderSave(byref(self._dgraph), byref(dordering), file_ptr)
        if ret != 0:
            raise lib.scotch_error(f"Failed to save distributed ordering to {filepath}", ret)

    @scotch_binding(
        "SCOTCH_dgraphOrderSaveMap",
        "int SCOTCH_dgraphOrderSaveMap(const SCOTCH_Dgraph *, const SCOTCH_Dordering *, FILE *)",
    )
    def order_save_map(self, dordering, filepath) -> None:
        """
        Save a distributed ordering as a block mapping file (root process).
        """
        with self._root_fopen(filepath, "w") as file_ptr:
            ret = lib.SCOTCH_dgraphOrderSaveMap(byref(self._dgraph), byref(dordering), file_ptr)
        if ret != 0:
            raise lib.scotch_error(f"Failed to save distributed ordering map to {filepath}", ret)

    @scotch_binding(
        "SCOTCH_dgraphOrderSaveTree",
        "int SCOTCH_dgraphOrderSaveTree(const SCOTCH_Dgraph *, const SCOTCH_Dordering *, FILE *)",
    )
    def order_save_tree(self, dordering, filepath) -> None:
        """
        Save the separator tree of a distributed ordering (root process).
        """
        with self._root_fopen(filepath, "w") as file_ptr:
            ret = lib.SCOTCH_dgraphOrderSaveTree(byref(self._dgraph), byref(dordering), file_ptr)
        if ret != 0:
            raise lib.scotch_error(f"Failed to save distributed ordering tree to {filepath}", ret)

    @scotch_binding(
        "SCOTCH_dgraphCorderInit",
        "int SCOTCH_dgraphCorderInit(const SCOTCH_Dgraph *, SCOTCH_Ordering *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *, SCOTCH_Num *)",
    )
    def corder_init(
        self,
        permtab: Optional[np.ndarray] = None,
        peritab: Optional[np.ndarray] = None,
        rangtab: Optional[np.ndarray] = None,
        treetab: Optional[np.ndarray] = None,
    ):
        """
        Initialize a centralized ordering to receive a gathered ordering.

        To be called on the root process before order_gather(). The provided
        arrays (each of length vertglbnbr, rangtab of vertglbnbr + 1) are
        filled by order_gather(); pass None for unwanted fields.

        Returns:
            An opaque SCOTCH_Ordering handle; release it with corder_exit().

        Raises:
            RuntimeError: If initialization fails
        """

        def output_pointer(array, name):
            # Scotch keeps these pointers and fills the arrays later (during
            # order_gather), so silent conversion copies would lose results.
            if array is None:
                return None
            if array.dtype != lib.get_scotch_dtype() or not array.flags["C_CONTIGUOUS"]:
                raise ValueError(
                    f"{name} must be a C-contiguous array of dtype "
                    f"{lib.get_scotch_dtype().__name__}"
                )
            return array.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        cordering = lib.SCOTCH_Ordering()
        cblkptr = lib.SCOTCH_Num()
        permtab_c = output_pointer(permtab, "permtab")
        peritab_c = output_pointer(peritab, "peritab")
        rangtab_c = output_pointer(rangtab, "rangtab")
        treetab_c = output_pointer(treetab, "treetab")
        ret = lib.SCOTCH_dgraphCorderInit(
            byref(self._dgraph),
            byref(cordering),
            permtab_c,
            peritab_c,
            byref(cblkptr),
            rangtab_c,
            treetab_c,
        )
        if ret != 0:
            raise lib.scotch_error("SCOTCH_dgraphCorderInit failed", ret)
        return cordering

    @scotch_binding(
        "SCOTCH_dgraphCorderExit",
        "void SCOTCH_dgraphCorderExit(const SCOTCH_Dgraph *, SCOTCH_Ordering *)",
    )
    def corder_exit(self, cordering) -> None:
        """Release a centralized ordering structure created by corder_init()."""
        lib.SCOTCH_dgraphCorderExit(byref(self._dgraph), byref(cordering))

    @scotch_binding(
        "SCOTCH_dgraphOrderGather",
        "int SCOTCH_dgraphOrderGather(const SCOTCH_Dgraph *, const SCOTCH_Dordering *, SCOTCH_Ordering *)",
    )
    def order_gather(self, dordering, cordering=None) -> None:
        """
        Gather a distributed ordering into a centralized ordering.

        Collective call. The root process passes the handle obtained from
        corder_init(); all other processes pass None.

        Raises:
            RuntimeError: If gathering fails
        """
        cordering_ptr = byref(cordering) if cordering is not None else None
        ret = lib.SCOTCH_dgraphOrderGather(byref(self._dgraph), byref(dordering), cordering_ptr)
        if ret != 0:
            raise lib.scotch_error("Failed to gather distributed ordering", ret)

    @highlevel_api(
        scotch_functions=[
            "SCOTCH_dgraphOrderInit",
            "SCOTCH_dgraphOrderCompute",
            "SCOTCH_dgraphOrderPerm",
            "SCOTCH_dgraphOrderExit",
        ]
    )
    def order(self, strategy=None) -> np.ndarray:
        """
        Compute a distributed ordering and return the local permutation.

        Collective call. Behaves like the sequential Graph.order(), but each
        process only receives the new indices of its own vertices.

        Args:
            strategy: Parallel ordering Strategy (optional)

        Returns:
            Array of length vertlocnbr: permloctab[i] is the new global index
            of local vertex i.

        Raises:
            RuntimeError: If the ordering fails
        """
        dordering = self.order_init()
        try:
            self.order_compute(dordering, strategy)
            return self.order_perm(dordering)
        finally:
            self.order_exit(dordering)
