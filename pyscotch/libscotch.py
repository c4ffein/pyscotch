"""
Low-level ctypes bindings to the PT-Scotch C library.

Single-Variant Design:
This module loads ONE Scotch variant based on environment variables:
- PYSCOTCH_INT_SIZE: 32 or 64 (default: 32)
- PYSCOTCH_PARALLEL: 0 or 1 (default: 0)

To test all variants, run the test suite 4 times with different configurations.
"""

import ctypes
import ctypes.util
import os
import sys
from ctypes import (
    c_int, c_long, c_double, c_char_p, c_void_p,
    POINTER, Structure, byref
)
from pathlib import Path
from typing import Optional

# =============================================================================
# Configuration from Environment
# =============================================================================

# Read configuration from environment (or use defaults)
_INT_SIZE = int(os.environ.get("PYSCOTCH_INT_SIZE", "32"))
_PARALLEL = os.environ.get("PYSCOTCH_PARALLEL", "0") == "1"

if _INT_SIZE not in (32, 64):
    raise ValueError(f"PYSCOTCH_INT_SIZE must be 32 or 64, got {_INT_SIZE}")

# =============================================================================
# Constants
# =============================================================================

# Graph coarsening flags (from scotch.h)
SCOTCH_COARSENNONE = 0x0000
SCOTCH_COARSENFOLD = 0x0100
SCOTCH_COARSENFOLDDUP = 0x0300
SCOTCH_COARSENNOMERGE = 0x4000

# =============================================================================
# Type Definitions
# =============================================================================

SCOTCH_Num = c_long if _INT_SIZE == 64 else c_int
SCOTCH_Idx = c_long if _INT_SIZE == 64 else c_int
SCOTCH_GraphPart2 = ctypes.c_ubyte

# =============================================================================
# Library Loading
# =============================================================================

def _get_lib_dir() -> Path:
    """Get the library directory for the current configuration."""
    builds_dir = Path(__file__).parent.parent / "scotch-builds"
    return builds_dir / f"lib{_INT_SIZE}"


def _preload_dependencies():
    """Preload shared dependencies (zlib, mpi) globally."""
    # Preload zlib
    try:
        zlib_path = ctypes.util.find_library('z')
        if zlib_path:
            ctypes.CDLL(zlib_path, mode=ctypes.RTLD_GLOBAL)
    except (OSError, AttributeError, TypeError):
        pass

    # Preload MPI if parallel
    if _PARALLEL:
        try:
            mpi_path = ctypes.util.find_library('mpi')
            if mpi_path:
                ctypes.CDLL(mpi_path, mode=ctypes.RTLD_GLOBAL)
        except (OSError, AttributeError, TypeError):
            pass


def _load_libraries():
    """Load the Scotch libraries."""
    lib_dir = _get_lib_dir()

    if not lib_dir.exists():
        raise FileNotFoundError(
            f"Scotch library directory not found: {lib_dir}\n"
            f"Run 'make build-all' to build Scotch variants."
        )

    # Load error library
    err_lib_path = lib_dir / "libscotcherr.so"
    if err_lib_path.exists():
        try:
            ctypes.CDLL(str(err_lib_path), mode=ctypes.RTLD_GLOBAL)
        except OSError as e:
            print(f"Warning: Could not load {err_lib_path}: {e}", file=sys.stderr)

    # Load sequential library (always needed)
    seq_lib_path = lib_dir / "libscotch.so"
    if not seq_lib_path.exists():
        raise FileNotFoundError(f"Sequential library not found: {seq_lib_path}")

    _lib_sequential = ctypes.CDLL(str(seq_lib_path), mode=ctypes.RTLD_GLOBAL)
    print(f"✓ Loaded Scotch: {_INT_SIZE}-bit from {seq_lib_path}", file=sys.stderr)

    # Load parallel library if needed
    _lib_parallel = None
    if _PARALLEL:
        par_lib_path = lib_dir / "libptscotch.so"
        if not par_lib_path.exists():
            raise FileNotFoundError(f"Parallel library not found: {par_lib_path}")

        _lib_parallel = ctypes.CDLL(str(par_lib_path), mode=ctypes.RTLD_GLOBAL)
        print(f"✓ Loaded PT-Scotch: {_INT_SIZE}-bit from {par_lib_path}", file=sys.stderr)

    return _lib_sequential, _lib_parallel


# Preload dependencies and load libraries
_preload_dependencies()
_lib_sequential, _lib_parallel = _load_libraries()

# =============================================================================
# Opaque Structure Definitions
# =============================================================================

def _make_opaque_struct(name: str, size: int):
    """Create an opaque ctypes Structure class with given size."""
    class OpaqueStruct(Structure):
        _fields_ = [("_opaque", ctypes.c_byte * size)]
    OpaqueStruct.__name__ = name
    OpaqueStruct.__qualname__ = name
    return OpaqueStruct


def _get_func(name: str):
    """Get a Scotch function with the correct suffix."""
    suffixed_name = f"{name}_{_INT_SIZE}"

    # Distributed graph functions are in the parallel library
    if name.lower().startswith("scotch_dgraph"):
        if not _lib_parallel:
            raise AttributeError(
                f"{name} requires PT-Scotch (parallel variant). "
                f"Set PYSCOTCH_PARALLEL=1 to enable."
            )
        return getattr(_lib_parallel, suffixed_name)

    # All other SCOTCH_* functions are in the sequential library
    return getattr(_lib_sequential, suffixed_name)


def _compute_structure_sizes():
    """Compute structure sizes using SCOTCH_*Sizeof() functions."""
    sizes = {}

    # Sequential structures (always available)
    sizes['graph'] = _get_func("SCOTCH_graphSizeof")()
    sizes['mesh'] = _get_func("SCOTCH_meshSizeof")()
    sizes['strat'] = _get_func("SCOTCH_stratSizeof")()
    sizes['arch'] = _get_func("SCOTCH_archSizeof")()
    sizes['mapping'] = _get_func("SCOTCH_mapSizeof")()
    sizes['ordering'] = _get_func("SCOTCH_orderSizeof")()
    sizes['geom'] = _get_func("SCOTCH_geomSizeof")()

    # Parallel structures (only if parallel variant)
    if _lib_parallel:
        sizes['dgraph'] = _get_func("SCOTCH_dgraphSizeof")()
    else:
        sizes['dgraph'] = None

    return sizes


# Compute sizes and define structures
_SIZES = _compute_structure_sizes()

SCOTCH_Graph = _make_opaque_struct("SCOTCH_Graph", _SIZES['graph'])
SCOTCH_Mesh = _make_opaque_struct("SCOTCH_Mesh", _SIZES['mesh'])
SCOTCH_Strat = _make_opaque_struct("SCOTCH_Strat", _SIZES['strat'])
SCOTCH_Arch = _make_opaque_struct("SCOTCH_Arch", _SIZES['arch'])
SCOTCH_Mapping = _make_opaque_struct("SCOTCH_Mapping", _SIZES['mapping'])
SCOTCH_Ordering = _make_opaque_struct("SCOTCH_Ordering", _SIZES['ordering'])
SCOTCH_Geom = _make_opaque_struct("SCOTCH_Geom", _SIZES['geom'])

if _SIZES['dgraph']:
    SCOTCH_Dgraph = _make_opaque_struct("SCOTCH_Dgraph", _SIZES['dgraph'])
else:
    SCOTCH_Dgraph = None

print(f"✓ Structure sizes: graph={_SIZES['graph']}, strat={_SIZES['strat']}, "
      f"arch={_SIZES['arch']}, dgraph={_SIZES['dgraph']}", file=sys.stderr)

# =============================================================================
# Function Bindings
# =============================================================================

def _bind_functions():
    """Bind all Scotch functions with proper type signatures."""
    # Get structure pointer types
    GraphPtr = POINTER(SCOTCH_Graph)
    MeshPtr = POINTER(SCOTCH_Mesh)
    StratPtr = POINTER(SCOTCH_Strat)
    ArchPtr = POINTER(SCOTCH_Arch)
    MappingPtr = POINTER(SCOTCH_Mapping)
    OrderingPtr = POINTER(SCOTCH_Ordering)
    GeomPtr = POINTER(SCOTCH_Geom)
    NumPtr = POINTER(SCOTCH_Num)
    IdxPtr = POINTER(SCOTCH_Idx)

    bindings = {}

    # --- Graph functions ---
    bindings['SCOTCH_graphInit'] = (c_int, [GraphPtr])
    bindings['SCOTCH_graphExit'] = (None, [GraphPtr])
    bindings['SCOTCH_graphBuild'] = (c_int, [
        GraphPtr, SCOTCH_Num, SCOTCH_Num,
        NumPtr, NumPtr, NumPtr, NumPtr,
        SCOTCH_Num, NumPtr, NumPtr
    ])
    bindings['SCOTCH_graphCheck'] = (c_int, [GraphPtr])
    bindings['SCOTCH_graphSize'] = (None, [GraphPtr, NumPtr, NumPtr])
    bindings['SCOTCH_graphData'] = (None, [
        GraphPtr, NumPtr, NumPtr, POINTER(NumPtr), POINTER(NumPtr),
        POINTER(NumPtr), POINTER(NumPtr), NumPtr, POINTER(NumPtr), POINTER(NumPtr)
    ])
    bindings['SCOTCH_graphLoad'] = (c_int, [GraphPtr, c_void_p, SCOTCH_Num, SCOTCH_Num])
    bindings['SCOTCH_graphSave'] = (c_int, [GraphPtr, c_void_p])
    bindings['SCOTCH_graphBase'] = (c_int, [GraphPtr, SCOTCH_Num])
    bindings['SCOTCH_graphPart'] = (c_int, [GraphPtr, SCOTCH_Num, StratPtr, NumPtr])
    bindings['SCOTCH_graphPartOvl'] = (c_int, [GraphPtr, SCOTCH_Num, StratPtr, NumPtr])
    bindings['SCOTCH_graphPartFixed'] = (c_int, [GraphPtr, SCOTCH_Num, StratPtr, NumPtr])
    bindings['SCOTCH_graphOrder'] = (c_int, [
        GraphPtr, StratPtr, NumPtr, NumPtr, NumPtr, NumPtr, NumPtr
    ])
    bindings['SCOTCH_graphCoarsen'] = (c_int, [
        GraphPtr, SCOTCH_Num, c_double, SCOTCH_Num, GraphPtr, NumPtr
    ])
    bindings['SCOTCH_graphCoarsenMatch'] = (c_int, [
        GraphPtr, NumPtr, c_double, SCOTCH_Num, NumPtr
    ])
    bindings['SCOTCH_graphCoarsenBuild'] = (c_int, [
        GraphPtr, SCOTCH_Num, NumPtr, GraphPtr, NumPtr
    ])
    bindings['SCOTCH_graphInduceList'] = (c_int, [GraphPtr, SCOTCH_Num, NumPtr, GraphPtr])
    bindings['SCOTCH_graphInducePart'] = (c_int, [GraphPtr, SCOTCH_Num, POINTER(SCOTCH_GraphPart2), SCOTCH_GraphPart2, GraphPtr])
    bindings['SCOTCH_graphDiamPV'] = (SCOTCH_Num, [GraphPtr])
    bindings['SCOTCH_graphColor'] = (c_int, [GraphPtr, NumPtr, NumPtr, SCOTCH_Num])
    bindings['SCOTCH_graphStat'] = (None, [
        GraphPtr, NumPtr, NumPtr, NumPtr, POINTER(c_double), POINTER(c_double),
        NumPtr, NumPtr, POINTER(c_double), POINTER(c_double),
        NumPtr, NumPtr, NumPtr, POINTER(c_double), POINTER(c_double)
    ])
    bindings['SCOTCH_graphMap'] = (c_int, [GraphPtr, ArchPtr, StratPtr, NumPtr])
    bindings['SCOTCH_graphMapInit'] = (c_int, [GraphPtr, MappingPtr, ArchPtr, NumPtr])
    bindings['SCOTCH_graphMapExit'] = (None, [GraphPtr, MappingPtr])
    bindings['SCOTCH_graphMapCompute'] = (c_int, [GraphPtr, MappingPtr, StratPtr])
    bindings['SCOTCH_graphRemapCompute'] = (c_int, [
        GraphPtr, MappingPtr, MappingPtr, c_double, NumPtr, StratPtr
    ])

    # --- Strategy functions ---
    bindings['SCOTCH_stratInit'] = (c_int, [StratPtr])
    bindings['SCOTCH_stratExit'] = (None, [StratPtr])
    bindings['SCOTCH_stratGraphMap'] = (c_int, [StratPtr, c_char_p])
    bindings['SCOTCH_stratGraphMapBuild'] = (c_int, [StratPtr, SCOTCH_Num, SCOTCH_Num, c_double])
    bindings['SCOTCH_stratGraphOrder'] = (c_int, [StratPtr, c_char_p])
    bindings['SCOTCH_stratGraphOrderBuild'] = (c_int, [StratPtr, SCOTCH_Num, SCOTCH_Num, c_double])
    bindings['SCOTCH_stratGraphPartOvl'] = (c_int, [StratPtr, c_char_p])
    bindings['SCOTCH_stratGraphPartOvlBuild'] = (c_int, [StratPtr, SCOTCH_Num, SCOTCH_Num, c_double])

    # --- Architecture functions ---
    bindings['SCOTCH_archInit'] = (c_int, [ArchPtr])
    bindings['SCOTCH_archExit'] = (None, [ArchPtr])
    bindings['SCOTCH_archCmplt'] = (c_int, [ArchPtr, SCOTCH_Num])
    bindings['SCOTCH_archCmpltw'] = (c_int, [ArchPtr, SCOTCH_Num, NumPtr])
    bindings['SCOTCH_archBuild0'] = (c_int, [ArchPtr, GraphPtr, SCOTCH_Num, NumPtr, StratPtr])
    bindings['SCOTCH_archBuild2'] = (c_int, [ArchPtr, GraphPtr, SCOTCH_Num, NumPtr])
    bindings['SCOTCH_archSub'] = (c_int, [ArchPtr, ArchPtr, SCOTCH_Num, NumPtr])
    bindings['SCOTCH_archLoad'] = (c_int, [ArchPtr, c_void_p])
    bindings['SCOTCH_archSave'] = (c_int, [ArchPtr, c_void_p])
    bindings['SCOTCH_archSize'] = (SCOTCH_Num, [ArchPtr])
    bindings['SCOTCH_archName'] = (c_char_p, [ArchPtr])

    # --- Mesh functions ---
    bindings['SCOTCH_meshInit'] = (c_int, [MeshPtr])
    bindings['SCOTCH_meshExit'] = (None, [MeshPtr])
    bindings['SCOTCH_meshLoad'] = (c_int, [MeshPtr, c_void_p, SCOTCH_Num])
    bindings['SCOTCH_meshSave'] = (c_int, [MeshPtr, c_void_p])
    bindings['SCOTCH_meshCheck'] = (c_int, [MeshPtr])
    bindings['SCOTCH_meshBuild'] = (c_int, [
        MeshPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num,
        NumPtr, NumPtr, NumPtr, NumPtr, NumPtr,
        SCOTCH_Num, NumPtr
    ])
    bindings['SCOTCH_meshGraph'] = (c_int, [MeshPtr, GraphPtr])
    bindings['SCOTCH_meshSize'] = (None, [MeshPtr, NumPtr, NumPtr, NumPtr])
    bindings['SCOTCH_meshData'] = (None, [
        MeshPtr, NumPtr, NumPtr, NumPtr, POINTER(NumPtr),
        POINTER(NumPtr), POINTER(NumPtr), POINTER(NumPtr), NumPtr, POINTER(NumPtr)
    ])

    # --- Geometry functions ---
    bindings['SCOTCH_geomInit'] = (c_int, [GeomPtr])
    bindings['SCOTCH_geomExit'] = (None, [GeomPtr])

    # --- Random functions ---
    bindings['SCOTCH_randomReset'] = (None, [])
    bindings['SCOTCH_randomSeed'] = (None, [SCOTCH_Num])
    bindings['SCOTCH_randomVal'] = (SCOTCH_Num, [SCOTCH_Num])
    bindings['SCOTCH_randomSave'] = (c_int, [c_void_p])  # FILE* as void*
    bindings['SCOTCH_randomLoad'] = (c_int, [c_void_p])  # FILE* as void*

    # --- Memory functions ---
    bindings['SCOTCH_memCur'] = (c_long, [])
    bindings['SCOTCH_memMax'] = (c_long, [])
    bindings['SCOTCH_memFree'] = (None, [c_void_p])

    # --- Version function ---
    bindings['SCOTCH_version'] = (None, [NumPtr, NumPtr, NumPtr])

    # Apply bindings
    for name, (restype, argtypes) in bindings.items():
        try:
            func = _get_func(name)
            func.restype = restype
            func.argtypes = argtypes
        except AttributeError:
            pass  # Function may not exist in all versions

    # --- Dgraph functions (parallel only) ---
    if _lib_parallel:
        DgraphPtr = POINTER(SCOTCH_Dgraph)

        dgraph_bindings = {
            'SCOTCH_dgraphInit': (c_int, [DgraphPtr, c_void_p]),  # MPI_Comm as void*
            'SCOTCH_dgraphExit': (None, [DgraphPtr]),
            'SCOTCH_dgraphBuild': (c_int, [
                DgraphPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num,
                NumPtr, NumPtr, NumPtr, NumPtr,  # vertloctab, vendloctab, veloloctab, vlblloctab
                SCOTCH_Num, SCOTCH_Num, NumPtr, NumPtr, NumPtr  # edgelocnbr, edgelocsiz, edgeloctab, edgegsttab, edloloctab
            ]),
            'SCOTCH_dgraphCheck': (c_int, [DgraphPtr]),
            'SCOTCH_dgraphData': (None, [
                DgraphPtr, NumPtr, NumPtr, NumPtr, NumPtr,
                POINTER(NumPtr), POINTER(NumPtr), POINTER(NumPtr), POINTER(NumPtr), POINTER(NumPtr),
                NumPtr, NumPtr, POINTER(NumPtr), POINTER(NumPtr), POINTER(NumPtr),
                c_void_p  # MPI_Comm*
            ]),
            'SCOTCH_dgraphLoad': (c_int, [DgraphPtr, c_void_p, SCOTCH_Num, SCOTCH_Num]),
            'SCOTCH_dgraphSave': (c_int, [DgraphPtr, c_void_p]),
            'SCOTCH_dgraphCoarsen': (c_int, [
                DgraphPtr, SCOTCH_Num, c_double, SCOTCH_Num, DgraphPtr, NumPtr
            ]),
            'SCOTCH_dgraphGhst': (c_int, [DgraphPtr]),
            'SCOTCH_dgraphGrow': (c_int, [DgraphPtr, SCOTCH_Num, NumPtr, SCOTCH_Num, NumPtr]),
            'SCOTCH_dgraphBand': (c_int, [DgraphPtr, SCOTCH_Num, NumPtr, SCOTCH_Num, DgraphPtr]),
            'SCOTCH_dgraphRedist': (c_int, [DgraphPtr, NumPtr, NumPtr, SCOTCH_Num, NumPtr, DgraphPtr]),
            'SCOTCH_dgraphInducePart': (c_int, [DgraphPtr, NumPtr, SCOTCH_Num, SCOTCH_Num, DgraphPtr]),
        }

        for name, (restype, argtypes) in dgraph_bindings.items():
            try:
                func = _get_func(name)
                func.restype = restype
                func.argtypes = argtypes
            except AttributeError:
                pass


# Bind all functions
_bind_functions()

# =============================================================================
# Public API
# =============================================================================

def get_scotch_int_size() -> int:
    """Return the SCOTCH_Num size in bits (32 or 64)."""
    return _INT_SIZE


def get_scotch_dtype():
    """Return the numpy dtype corresponding to SCOTCH_Num."""
    import numpy as np
    return np.int32 if _INT_SIZE == 32 else np.int64


def get_dtype():
    """Alias for get_scotch_dtype()."""
    return get_scotch_dtype()


def is_parallel() -> bool:
    """Return True if PT-Scotch (parallel) variant is loaded."""
    return _PARALLEL


# =============================================================================
# Wrapped functions with validation
# =============================================================================

def _wrapped_randomVal(randmax):
    """Wrapper for SCOTCH_randomVal with input validation.

    Validates that randmax > 0 to prevent floating-point exception
    in the underlying C function (divide by zero).
    """
    if randmax <= 0:
        raise ValueError(f"SCOTCH_randomVal requires randmax > 0, got {randmax}")
    return _get_func("SCOTCH_randomVal")(randmax)


# Registry of wrapped functions
_WRAPPED_FUNCTIONS = {
    "SCOTCH_randomVal": _wrapped_randomVal,
}


# =============================================================================
# Module-level function access
# =============================================================================

def __getattr__(name: str):
    """Provide attribute access for Scotch functions."""
    # Check for wrapped functions first
    if name in _WRAPPED_FUNCTIONS:
        return _WRAPPED_FUNCTIONS[name]

    if name.startswith("SCOTCH_"):
        try:
            return _get_func(name)
        except AttributeError:
            raise AttributeError(f"module 'libscotch' has no attribute '{name}'")
    raise AttributeError(f"module 'libscotch' has no attribute '{name}'")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Configuration
    "get_scotch_int_size",
    "get_scotch_dtype",
    "get_dtype",
    "is_parallel",
    # Types
    "SCOTCH_Num",
    "SCOTCH_Idx",
    "SCOTCH_GraphPart2",
    # Structures
    "SCOTCH_Graph",
    "SCOTCH_Mesh",
    "SCOTCH_Strat",
    "SCOTCH_Arch",
    "SCOTCH_Mapping",
    "SCOTCH_Ordering",
    "SCOTCH_Geom",
    "SCOTCH_Dgraph",
    # Constants
    "SCOTCH_COARSENNONE",
    "SCOTCH_COARSENFOLD",
    "SCOTCH_COARSENFOLDDUP",
    "SCOTCH_COARSENNOMERGE",
]
