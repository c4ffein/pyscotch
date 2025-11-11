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
from .strategy import Strategy
from .arch import Architecture
from .mapping import Mapping
from .ordering import Ordering
from .libscotch import get_scotch_int_size, get_scotch_dtype

__version__ = "0.1.0"
__all__ = [
    "Graph",
    "Mesh",
    "Strategy",
    "Architecture",
    "Mapping",
    "Ordering",
    "get_scotch_int_size",
    "get_scotch_dtype",
]
