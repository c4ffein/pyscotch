"""
PyScotch - Python wrapper for PT-Scotch library

Provides Python bindings for the PT-Scotch graph partitioning library.
"""

from .graph import Graph
from .mesh import Mesh
from .strategy import Strategy
from .arch import Architecture
from .mapping import Mapping
from .ordering import Ordering

__version__ = "0.1.0"
__all__ = [
    "Graph",
    "Mesh",
    "Strategy",
    "Architecture",
    "Mapping",
    "Ordering",
]
