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
from .api_decorators import scotch_binding  # Scotch-free at import
from . import mpi  # Scotch-free at import (ctypes-only MPI wrapper)
from ctypes import byref

# Lazy attribute access (PEP 562). Importing any of these submodules loads the
# Scotch shared libraries, so we defer them to first use. This keeps a bare
# `import pyscotch` cheap and — crucially — lets `pyscotch doctor` run to
# DIAGNOSE a broken/missing Scotch instead of crashing on import with the very
# load error it exists to explain. `from pyscotch import Graph` still works
# (it triggers __getattr__ below).
_LAZY = {
    "Graph": ("graph", "Graph"),
    "Mesh": ("mesh", "Mesh"),
    "Strategy": ("strategy", "Strategy"),
    "Strategies": ("strategy", "Strategies"),
    "StrategyFlags": ("strategy", "StrategyFlags"),
    "Architecture": ("arch", "Architecture"),
    "Mapping": ("mapping", "Mapping"),
    "Ordering": ("ordering", "Ordering"),
    "Dgraph": ("dgraph", "Dgraph"),
    "Context": ("context", "Context"),
    "Geometry": ("geom", "Geometry"),
    "get_scotch_int_size": ("libscotch", "get_scotch_int_size"),
    "get_scotch_dtype": ("libscotch", "get_scotch_dtype"),
    "SCOTCH_COARSENNONE": ("libscotch", "SCOTCH_COARSENNONE"),
    "SCOTCH_COARSENFOLD": ("libscotch", "SCOTCH_COARSENFOLD"),
    "SCOTCH_COARSENFOLDDUP": ("libscotch", "SCOTCH_COARSENFOLDDUP"),
    "SCOTCH_COARSENNOMERGE": ("libscotch", "SCOTCH_COARSENNOMERGE"),
}


def __getattr__(name):
    """PEP 562 lazy loader for the Scotch-backed public API."""
    if name in _LAZY:
        import importlib

        modname, attr = _LAZY[name]
        return getattr(importlib.import_module(f".{modname}", __name__), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals()) + list(_LAZY))


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


@scotch_binding("SCOTCH_randomProc", "void SCOTCH_randomProc(int)")
def random_proc(procnum: int) -> None:
    """Fold a process number into the PRNG seed (decorrelates ranks).

    By default the seed ignores the process rank, so all ranks draw identical
    sequences. Call this (then ``random_reset()``) when you want each rank to
    draw an independent stream; ``random_proc(0)`` restores the default.
    """
    from . import libscotch as lib

    lib.SCOTCH_randomProc(procnum)


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
    "StrategyFlags",
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
    "random_proc",
    "mem_cur",
    "mem_max",
    "get_scotch_int_size",
    "get_scotch_dtype",
    "SCOTCH_COARSENNONE",
    "SCOTCH_COARSENFOLD",
    "SCOTCH_COARSENFOLDDUP",
    "SCOTCH_COARSENNOMERGE",
]
