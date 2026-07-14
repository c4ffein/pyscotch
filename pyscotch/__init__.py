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

from ._version import __version__  # single source of truth (CI stamps it from the tag)
from .api_decorators import scotch_binding
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


@scotch_binding("SCOTCH_version", "void SCOTCH_version(int *, int *, int *)")
def scotch_version() -> tuple:
    """
    Get the Scotch library version.

    Returns:
        Tuple of (major, minor, patch) version numbers
    """
    from ctypes import c_int
    from . import libscotch as lib

    major = c_int()
    minor = c_int()
    patch = c_int()
    lib.SCOTCH_version(byref(major), byref(minor), byref(patch))
    return (major.value, minor.value, patch.value)


@scotch_binding("SCOTCH_randomReset", "void SCOTCH_randomReset(void)")
def random_reset() -> None:
    """Reset Scotch's pseudorandom number generator to its initial state."""
    from . import libscotch as lib

    lib.SCOTCH_randomReset()


@scotch_binding("SCOTCH_randomSeed", "void SCOTCH_randomSeed(SCOTCH_Num)")
def random_seed(seed: int) -> None:
    """Set the seed of Scotch's pseudorandom number generator."""
    from . import libscotch as lib

    lib.SCOTCH_randomSeed(lib.SCOTCH_Num(seed))


@scotch_binding("SCOTCH_memCur", "SCOTCH_Idx SCOTCH_memCur(void)")
def mem_cur() -> int:
    """Get current Scotch memory usage in bytes (requires SCOTCH_DEBUG_MEM)."""
    from . import libscotch as lib

    return lib.SCOTCH_memCur()


@scotch_binding("SCOTCH_memMax", "SCOTCH_Idx SCOTCH_memMax(void)")
def mem_max() -> int:
    """Get peak Scotch memory usage in bytes (requires SCOTCH_DEBUG_MEM)."""
    from . import libscotch as lib

    return lib.SCOTCH_memMax()


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
