"""
Distributed Graph (PT-Scotch) API.

This module provides a Pythonic interface to PT-Scotch's distributed graph
operations, which use MPI for parallel processing.
"""
import numpy as np
from pathlib import Path
from ctypes import byref, POINTER, c_int
from typing import Optional

from pyscotch.libscotch import (
    SCOTCH_Dgraph,
    SCOTCH_COARSENNONE as COARSEN_NONE,
    SCOTCH_COARSENFOLD as COARSEN_FOLD,
    SCOTCH_COARSENFOLDDUP as COARSEN_FOLDDUP,
    SCOTCH_COARSENNOMERGE as COARSEN_NOMERGE,
)
from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.graph import c_fopen


class Dgraph:
    """
    Distributed graph for PT-Scotch parallel partitioning and ordering.

    A distributed graph (Dgraph) represents a graph that is partitioned across
    multiple MPI processes. Each process holds a portion of the vertices and edges.

    This requires:
    - PT-Scotch library loaded (parallel variant)
    - MPI initialized
    - Running in an MPI environment (e.g., via mpirun/mpiexec)

    Example:
        >>> from pyscotch import mpi, Dgraph
        >>> from pyscotch import libscotch as lib
        >>>
        >>> # Initialize MPI
        >>> mpi.init()
        >>>
        >>> # Set parallel variant
        >>> lib.set_active_variant(64, parallel=True)
        >>>
        >>> # Create distributed graph
        >>> dgraph = Dgraph()
        >>>
        >>> # Build from distributed data
        >>> # (each MPI rank provides its local portion)
        >>> dgraph.build(vertloctab, edgeloctab, baseval=0)
        >>>
        >>> # Operations like partitioning would go here
        >>>
        >>> # Cleanup
        >>> mpi.finalize()
    """

    def __init__(self, comm=None):
        """
        Initialize a distributed graph.

        Args:
            comm: MPI communicator (default: MPI_COMM_WORLD).
                  Can be a ctypes.c_void_p representing an MPI_Comm.

        Raises:
            RuntimeError: If PT-Scotch (parallel variant) is not loaded
            RuntimeError: If MPI is not available
        """
        # Check that parallel variant is loaded
        variant = lib.get_active_variant()
        if not variant or not variant.parallel:
            raise RuntimeError(
                "Dgraph requires PT-Scotch (parallel variant).\n"
                "Use lib.set_active_variant(int_size, parallel=True) first."
            )

        # Get MPI communicator
        if comm is None:
            if not mpi.is_initialized():
                raise RuntimeError(
                    "MPI must be initialized before creating Dgraph.\n"
                    "Call mpi.init() first."
                )
            comm = mpi.get_comm_world()

        # Save communicator for later use (e.g., in coarsen)
        self._comm = comm

        # Initialize distributed graph
        self._dgraph = SCOTCH_Dgraph()
        self._exit_called = False
        ret = lib.SCOTCH_dgraphInit(byref(self._dgraph), comm)
        if ret != 0:
            raise RuntimeError(f"SCOTCH_dgraphExit failed with error {ret}")

    def __del__(self):
        """Cleanup the distributed graph."""
        if hasattr(self, '_dgraph') and not getattr(self, '_exit_called', False):
            try:
                # Only cleanup if MPI is still initialized
                # If MPI is finalized, PT-Scotch cleanup will fail
                if mpi.is_initialized():
                    lib.SCOTCH_dgraphExit(byref(self._dgraph))
                    self._exit_called = True
            except:
                pass

    def exit(self):
        """Explicitly cleanup the distributed graph.

        Call this before MPI finalize to ensure proper cleanup.
        """
        if hasattr(self, '_dgraph') and not self._exit_called:
            lib.SCOTCH_dgraphExit(byref(self._dgraph))
            self._exit_called = True

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
        dtype = lib.get_dtype()
        vertloctab = np.asarray(vertloctab, dtype=dtype)
        edgeloctab = np.asarray(edgeloctab, dtype=dtype)

        # Calculate sizes
        vertlocnbr = len(vertloctab) - 1  # Number of local vertices
        vertlocmax = vertlocnbr  # Maximum local vertex index
        edgelocnbr = len(edgeloctab)  # Number of local edges
        edgelocsiz = edgelocnbr  # Size of edge array

        # Handle optional arrays
        if vendloctab is None:
            vendloctab_ptr = None
        else:
            vendloctab = np.asarray(vendloctab, dtype=dtype)
            vendloctab_ptr = vendloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        if veloloctab is None:
            veloloctab_ptr = None
        else:
            veloloctab = np.asarray(veloloctab, dtype=dtype)
            veloloctab_ptr = veloloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        if vlblloctab is None:
            vlblloctab_ptr = None
        else:
            vlblloctab = np.asarray(vlblloctab, dtype=dtype)
            vlblloctab_ptr = vlblloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        if edgegsttab is None:
            edgegsttab_ptr = None
        else:
            edgegsttab = np.asarray(edgegsttab, dtype=dtype)
            edgegsttab_ptr = edgegsttab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        if edloloctab is None:
            edloloctab_ptr = None
        else:
            edloloctab = np.asarray(edloloctab, dtype=dtype)
            edloloctab_ptr = edloloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))

        # Build the distributed graph
        ret = lib.SCOTCH_dgraphBuild(
            byref(self._dgraph),
            lib.SCOTCH_Num(baseval),
            lib.SCOTCH_Num(vertlocnbr),
            lib.SCOTCH_Num(vertlocmax),
            vertloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            vendloctab_ptr,
            veloloctab_ptr,
            vlblloctab_ptr,
            lib.SCOTCH_Num(edgelocnbr),
            lib.SCOTCH_Num(edgelocsiz),
            edgeloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            edgegsttab_ptr,
            edloloctab_ptr,
        )

        if ret != 0:
            raise RuntimeError(f"SCOTCH_dgraphBuild failed with error {ret}")

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
        rank = mpi.comm_rank()

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
            raise RuntimeError(f"Failed to load distributed graph from {filepath}")

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
            raise RuntimeError(f"Failed to save distributed graph to {filepath}")

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
        commptr = c_int() if want_commptr else None

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
            result['baseval'] = baseval.value
        if want_vertglbnbr:
            result['vertglbnbr'] = vertglbnbr.value
        if want_vertlocnbr:
            result['vertlocnbr'] = vertlocnbr.value
        if want_vertlocmax:
            result['vertlocmax'] = vertlocmax.value
        if want_vertgstnbr:
            result['vertgstnbr'] = vertgstnbr.value
        if want_vertloctab:
            result['vertloctab'] = vertloctab
        if want_vendloctab:
            result['vendloctab'] = vendloctab
        if want_veloloctab:
            result['veloloctab'] = veloloctab
        if want_vlblloctab:
            result['vlblloctab'] = vlblloctab
        if want_edgeglbnbr:
            result['edgeglbnbr'] = edgeglbnbr.value
        if want_edgelocnbr:
            result['edgelocnbr'] = edgelocnbr.value
        if want_edgelocsiz:
            result['edgelocsiz'] = edgelocsiz.value
        if want_edgeloctab:
            result['edgeloctab'] = edgeloctab
        if want_edgegsttab:
            result['edgegsttab'] = edgegsttab
        if want_edloloctab:
            result['edloloctab'] = edloloctab
        if want_commptr:
            result['commptr'] = commptr.value

        return result

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
        result = lib.SCOTCH_dgraphCoarsenVertLocMax(
            byref(self._dgraph),
            lib.SCOTCH_Num(foldval)
        )
        return int(result)

    def coarsen(
        self,
        coarrat: float = 0.8,
        foldval: int = COARSEN_NONE,
        flags: int = 0
    ) -> tuple['Dgraph', Optional[np.ndarray]]:
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

        # Create coarse graph
        coarse_graph = Dgraph(comm=self._comm)

        # Perform coarsening
        ret = lib.SCOTCH_dgraphCoarsen(
            byref(self._dgraph),
            lib.SCOTCH_Num(flags),
            float(coarrat),
            lib.SCOTCH_Num(foldval),
            byref(coarse_graph._dgraph),
            multloctab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )

        if ret == 0:
            # Success - graph was coarsened
            return (coarse_graph, multloctab)
        elif ret == 1:
            # Graph could not be coarsened (not an error)
            # This can happen if graph is too small or already optimal
            return (coarse_graph, None)
        else:
            # Error
            raise RuntimeError(f"Failed to coarsen graph (error code {ret})")
