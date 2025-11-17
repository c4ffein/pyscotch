"""
Distributed Graph (PT-Scotch) API.

This module provides a Pythonic interface to PT-Scotch's distributed graph
operations, which use MPI for parallel processing.
"""
import numpy as np
from pathlib import Path
from ctypes import byref, POINTER, c_int
from typing import Optional

from pyscotch.libscotch import SCOTCH_Dgraph
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

    def data(self):
        """
        Get the internal data arrays of the distributed graph.

        Returns:
            Dictionary containing:
            - baseval: Base value
            - vertlocnbr: Number of local vertices
            - vertlocmax: Maximum local vertex
            - vertloctab: Local vertex array (or None)
            - vendloctab: Local vertex end array (or None)
            - veloloctab: Local vertex weights (or None)
            - vlblloctab: Local vertex labels (or None)
            - edgelocnbr: Number of local edges
            - edgelocsiz: Size of edge array
            - edgeloctab: Local edge array (or None)
            - edgegsttab: Ghost edge array (or None)
            - edloloctab: Local edge weights (or None)

        Note:
            The returned arrays are pointers to internal Scotch data.
            Do not modify them or use after the graph is destroyed.
        """
        baseval = lib.SCOTCH_Num()
        vertlocnbr = lib.SCOTCH_Num()
        vertlocmax = lib.SCOTCH_Num()
        vertloctab = POINTER(lib.SCOTCH_Num)()
        vendloctab = POINTER(lib.SCOTCH_Num)()
        veloloctab = POINTER(lib.SCOTCH_Num)()
        vlblloctab = POINTER(lib.SCOTCH_Num)()
        edgelocnbr = lib.SCOTCH_Num()
        edgelocsiz = lib.SCOTCH_Num()
        edgeloctab = POINTER(lib.SCOTCH_Num)()
        edgegsttab = POINTER(lib.SCOTCH_Num)()
        edloloctab = POINTER(lib.SCOTCH_Num)()

        lib.SCOTCH_dgraphData(
            byref(self._dgraph),
            byref(baseval),
            byref(vertlocnbr),
            byref(vertlocmax),
            byref(vertloctab),
            byref(vendloctab),
            byref(veloloctab),
            byref(vlblloctab),
            byref(edgelocnbr),
            byref(edgelocsiz),
            byref(edgeloctab),
            byref(edgegsttab),
            byref(edloloctab),
        )

        return {
            'baseval': baseval.value,
            'vertlocnbr': vertlocnbr.value,
            'vertlocmax': vertlocmax.value,
            'vertloctab': vertloctab,
            'vendloctab': vendloctab,
            'veloloctab': veloloctab,
            'vlblloctab': vlblloctab,
            'edgelocnbr': edgelocnbr.value,
            'edgelocsiz': edgelocsiz.value,
            'edgeloctab': edgeloctab,
            'edgegsttab': edgegsttab,
            'edloloctab': edloloctab,
        }
