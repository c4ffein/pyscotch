"""
PyScotch - Python wrapper for PT-Scotch library

Provides Python bindings for the PT-Scotch graph partitioning library.

This package offers:
- Graph partitioning for distributed computing
- Mesh partitioning for parallel processing
- Sparse matrix ordering for efficient factorization
- High-level Python API with comprehensive type hints
- Command-line interface for common operations

Example:
    >>> from pyscotch import Graph
    >>> graph = Graph()
    >>> graph.load("input.grf")
    >>> partitions = graph.partition(nparts=4)
"""

from .graph import Graph
from .mesh import Mesh
from .strategy import Strategy, Strategies
from .arch import Architecture
from .mapping import Mapping
from .ordering import Ordering
from .dgraph import Dgraph
from .context import Context
from .geom import Geometry
from . import mpi
from .libscotch import (
    get_scotch_int_size,
    get_scotch_dtype,
    SCOTCH_COARSENNONE,
    SCOTCH_COARSENFOLD,
    SCOTCH_COARSENFOLDDUP,
    SCOTCH_COARSENNOMERGE,
)
from ctypes import byref


def scotch_version() -> tuple:
    """
    Get the Scotch library version.

    Returns:
        Tuple of (major, minor, patch) version numbers
    """
    from . import libscotch as lib
    major = lib.SCOTCH_Num()
    minor = lib.SCOTCH_Num()
    patch = lib.SCOTCH_Num()
    lib.SCOTCH_version(byref(major), byref(minor), byref(patch))
    return (major.value, minor.value, patch.value)


def random_reset() -> None:
    """Reset Scotch's pseudorandom number generator to its initial state."""
    from . import libscotch as lib
    lib.SCOTCH_randomReset()


def random_seed(seed: int) -> None:
    """Set the seed of Scotch's pseudorandom number generator."""
    from . import libscotch as lib
    lib.SCOTCH_randomSeed(lib.SCOTCH_Num(seed))


def mem_cur() -> int:
    """Get current Scotch memory usage in bytes (requires SCOTCH_DEBUG_MEM)."""
    from . import libscotch as lib
    return lib.SCOTCH_memCur()


def mem_max() -> int:
    """Get peak Scotch memory usage in bytes (requires SCOTCH_DEBUG_MEM)."""
    from . import libscotch as lib
    return lib.SCOTCH_memMax()


__version__ = "0.1.0"
__all__ = [
    "Graph",
    "Mesh",
    "Strategy",
    "Strategies",
    "Architecture",
    "Mapping",
    "Ordering",
    "Dgraph",
    "Context",
    "Geometry",
    "mpi",
    "scotch_version",
    "random_reset",
    "random_seed",
    "mem_cur",
    "mem_max",
    "get_scotch_int_size",
    "get_scotch_dtype",
    "SCOTCH_COARSENNONE",
    "SCOTCH_COARSENFOLD",
    "SCOTCH_COARSENFOLDDUP",
    "SCOTCH_COARSENNOMERGE",
]
