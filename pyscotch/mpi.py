"""
Simple MPI wrapper using ctypes (no mpi4py needed).

This provides the minimal MPI functionality needed for PT-Scotch's
distributed graph operations.
"""
import ctypes
import ctypes.util
from typing import Optional
import sys


class MPI:
    """Minimal MPI wrapper for PT-Scotch."""

    def __init__(self):
        self._libmpi: Optional[ctypes.CDLL] = None
        self._initialized = False
        self._comm_world = None

    def _load(self):
        """Load MPI library."""
        if self._libmpi:
            return

        mpi_path = ctypes.util.find_library('mpi')
        if not mpi_path:
            raise RuntimeError(
                "MPI library not found. PT-Scotch requires MPI.\n"
                "Please install an MPI implementation (OpenMPI, MPICH, etc.)"
            )

        self._libmpi = ctypes.CDLL(mpi_path, mode=ctypes.RTLD_GLOBAL)

        # Bind MPI functions
        self._libmpi.MPI_Init.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p))
        ]
        self._libmpi.MPI_Init.restype = ctypes.c_int

        self._libmpi.MPI_Finalize.argtypes = []
        self._libmpi.MPI_Finalize.restype = ctypes.c_int

        self._libmpi.MPI_Initialized.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self._libmpi.MPI_Initialized.restype = ctypes.c_int

        self._libmpi.MPI_Comm_size.argtypes = [
            ctypes.c_void_p,  # MPI_Comm
            ctypes.POINTER(ctypes.c_int)
        ]
        self._libmpi.MPI_Comm_size.restype = ctypes.c_int

        self._libmpi.MPI_Comm_rank.argtypes = [
            ctypes.c_void_p,  # MPI_Comm
            ctypes.POINTER(ctypes.c_int)
        ]
        self._libmpi.MPI_Comm_rank.restype = ctypes.c_int

        self._libmpi.MPI_Barrier.argtypes = [ctypes.c_void_p]  # MPI_Comm
        self._libmpi.MPI_Barrier.restype = ctypes.c_int

        # MPI_COMM_WORLD - try different methods to get it
        self._comm_world = self._get_comm_world()

    def _get_comm_world(self):
        """Get MPI_COMM_WORLD constant (implementation-specific)."""
        # Method 1: Try OpenMPI - it's a pointer to a global struct
        try:
            comm_ptr = ctypes.c_void_p.in_dll(self._libmpi, 'ompi_mpi_comm_world')
            return ctypes.addressof(comm_ptr)
        except:
            pass

        # Method 2: Try MPICH - it's often an integer constant
        # The value 0x44000000 is MPICH's MPI_COMM_WORLD
        try:
            # For MPICH, we can try to get it from the library
            # but it's usually just a constant
            return 0x44000000
        except:
            pass

        # Method 3: Try Intel MPI
        try:
            comm_ptr = ctypes.c_void_p.in_dll(self._libmpi, 'I_MPI_COMM_WORLD')
            return ctypes.addressof(comm_ptr)
        except:
            pass

        raise RuntimeError(
            "Could not determine MPI_COMM_WORLD.\n"
            "Your MPI implementation may not be supported.\n"
            "Supported: OpenMPI, MPICH, Intel MPI"
        )

    def init(self) -> int:
        """Initialize MPI (like MPI_Init).

        Returns:
            0 on success, error code otherwise
        """
        self._load()

        # Check if already initialized
        flag = ctypes.c_int()
        self._libmpi.MPI_Initialized(ctypes.byref(flag))
        if flag.value:
            self._initialized = True
            return 0

        # Initialize MPI with NULL arguments (Python already has sys.argv)
        argc = ctypes.c_int(0)
        argv = ctypes.POINTER(ctypes.c_char_p)()
        ret = self._libmpi.MPI_Init(ctypes.byref(argc), ctypes.byref(argv))

        if ret == 0:
            self._initialized = True
        else:
            print(f"Warning: MPI_Init returned {ret}", file=sys.stderr)

        return ret

    def finalize(self) -> int:
        """Finalize MPI.

        Returns:
            0 on success, error code otherwise
        """
        if not self._libmpi or not self._initialized:
            return 0

        ret = self._libmpi.MPI_Finalize()
        if ret == 0:
            self._initialized = False
        return ret

    def is_initialized(self) -> bool:
        """Check if MPI is initialized."""
        if not self._libmpi:
            return False

        flag = ctypes.c_int()
        self._libmpi.MPI_Initialized(ctypes.byref(flag))
        return bool(flag.value)

    def get_comm_world(self) -> ctypes.c_void_p:
        """Get MPI_COMM_WORLD as c_void_p for passing to Scotch.

        Returns:
            MPI_COMM_WORLD communicator
        """
        self._load()
        return ctypes.c_void_p(self._comm_world)

    def comm_size(self, comm=None) -> int:
        """Get communicator size.

        Args:
            comm: MPI communicator (default: MPI_COMM_WORLD)

        Returns:
            Number of processes in the communicator
        """
        if comm is None:
            comm = self.get_comm_world()
        size = ctypes.c_int()
        ret = self._libmpi.MPI_Comm_size(comm, ctypes.byref(size))
        if ret != 0:
            raise RuntimeError(f"MPI_Comm_size failed with error {ret}")
        return size.value

    def comm_rank(self, comm=None) -> int:
        """Get rank in communicator.

        Args:
            comm: MPI communicator (default: MPI_COMM_WORLD)

        Returns:
            Process rank (0 to size-1)
        """
        if comm is None:
            comm = self.get_comm_world()
        rank = ctypes.c_int()
        ret = self._libmpi.MPI_Comm_rank(comm, ctypes.byref(rank))
        if ret != 0:
            raise RuntimeError(f"MPI_Comm_rank failed with error {ret}")
        return rank.value

    def barrier(self, comm=None) -> int:
        """Synchronize all processes in communicator.

        Blocks until all processes in the communicator have reached this call.
        Useful for:
        - Ensuring all processes finish a stage before continuing
        - Synchronizing output for cleaner debug messages
        - Debugging race conditions

        Args:
            comm: MPI communicator (default: MPI_COMM_WORLD)

        Returns:
            0 on success, error code otherwise
        """
        if comm is None:
            comm = self.get_comm_world()
        ret = self._libmpi.MPI_Barrier(comm)
        if ret != 0:
            raise RuntimeError(f"MPI_Barrier failed with error {ret}")
        return ret


# Global MPI instance
mpi = MPI()
