"""
Architecture class for PT-Scotch target architectures.
"""

from ctypes import byref

try:
    from . import libscotch as lib
    _lib_available = lib._libscotch is not None
except ImportError:
    _lib_available = False


class Architecture:
    """
    Represents a target architecture for graph mapping.

    An architecture defines the topology of the target machine or domain
    decomposition onto which a graph will be mapped.
    """

    def __init__(self):
        """Initialize an architecture."""
        if not _lib_available:
            raise RuntimeError(
                "Scotch library not available. Build it with 'make build-scotch'"
            )

        self._arch = lib.SCOTCH_Arch()
        ret = lib.SCOTCH_archInit(byref(self._arch))
        if ret != 0:
            raise RuntimeError(f"Failed to initialize architecture (error code: {ret})")

        self._initialized = True

    def __del__(self):
        """Clean up architecture resources."""
        if hasattr(self, "_initialized") and self._initialized:
            lib.SCOTCH_archExit(byref(self._arch))

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
