"""
Low-level ctypes bindings to the PT-Scotch C library.

Single-Variant Design:
This module loads ONE Scotch variant based on environment variables:
- PYSCOTCH_INT_SIZE: 32 or 64 (default: 64)
- PYSCOTCH_PARALLEL: 0 or 1 (default: 0)

To test all variants, run the test suite 4 times with different configurations.
"""

import ctypes
import ctypes.util
import os
import sys

import numpy as np
from ctypes import c_int, c_long, c_double, c_char_p, c_void_p, POINTER, Structure, byref
from pathlib import Path
from typing import Optional

from .api_decorators import internal_api

# =============================================================================
# Configuration from Environment
# =============================================================================

# Read configuration from environment (or use defaults)
_INT_SIZE = int(os.environ.get("PYSCOTCH_INT_SIZE", "64"))
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

# 3D grid distributed graph building flags (from ptscotch.h)
SCOTCH_DGRAPHBUILDGRID3DGRID = 0
SCOTCH_DGRAPHBUILDGRID3DTORUS = 2
SCOTCH_DGRAPHBUILDGRID3DNGB6 = 0
SCOTCH_DGRAPHBUILDGRID3DNGB26 = 1
SCOTCH_DGRAPHBUILDGRID3DVERTLOAD = 4
SCOTCH_DGRAPHBUILDGRID3DEDGELOAD = 8

# =============================================================================
# Type Definitions
# =============================================================================

SCOTCH_Num = c_long if _INT_SIZE == 64 else c_int
SCOTCH_Idx = c_long if _INT_SIZE == 64 else c_int
SCOTCH_GraphPart2 = ctypes.c_ubyte

# =============================================================================
# Library Loading
# =============================================================================


def _get_lib_dir() -> Optional[Path]:
    """Get the library directory for the current configuration.

    Search order:
    1. PYSCOTCH_SYSTEM=1 forces system-installed Scotch (returns None)
    2. PYSCOTCH_LIB_DIR environment variable (explicit override)
    3. pyscotch/_libs/lib{32,64}/ (libraries bundled inside an installed wheel)
    4. scotch-builds/lib{32,64}/ next to the repo (development layout)
    5. None: fall back to the system-installed Scotch (dlopen by soname)
    """
    if os.environ.get("PYSCOTCH_SYSTEM") == "1":
        return None
    env_dir = os.environ.get("PYSCOTCH_LIB_DIR")
    if env_dir:
        return Path(env_dir)
    packaged_dir = Path(__file__).parent / "_libs" / f"lib{_INT_SIZE}"
    if packaged_dir.exists():
        return packaged_dir
    builds_dir = Path(__file__).parent.parent / "scotch-builds" / f"lib{_INT_SIZE}"
    if builds_dir.exists():
        return builds_dir
    return None


def _dlopen_system(short_name, sonames):
    """Load a library from the system linker paths, or return None.

    Tries ctypes.util.find_library first (ldconfig cache), then dlopen on a
    list of candidate sonames (which also honors LD_LIBRARY_PATH).
    """
    found = ctypes.util.find_library(short_name)
    candidates = ([found] if found else []) + list(sonames)
    for name in candidates:
        try:
            return ctypes.CDLL(name, mode=ctypes.RTLD_GLOBAL)
        except OSError:
            continue
    return None


# Runtime sonames of dependencies that Scotch's as-built libraries under-declare.
#
# Upstream root cause: Scotch links libscotch.so with `gcc -shared -o ... *.o`
# and no `-lz`/`-lm`/`-pthread` (those go only on its executable links), so the
# library calls libz but records no NEEDED entry for it. The proper fix is in
# Scotch's build (link the .so with its libs, or `-Wl,--no-undefined`) and is
# worth raising with the team politely — it would help everyone who loads the
# bare .so. Until then we compensate in two independent layers, either of which
# is sufficient on its own:
#   1. scripts/build_wheel_libs.sh (build time): stamp the honest NEEDED entries
#      onto the *bundled wheel* .so. Cannot reach a system-installed Scotch.
#   2. HERE (runtime): preload the dependency RTLD_GLOBAL before Scotch loads —
#      this covers every source (bundled, PYSCOTCH_LIB_DIR, and a system/conda
#      Scotch that is itself under-linked), for which layer 1 can do nothing.
#
# The *versioned runtime* soname comes first on purpose: ctypes.util.find_library
# ("z") resolves the `libz.so` devel symlink (via gcc/ld/ldconfig) and returns
# None in a clean `pip install` environment with no -dev packages — exactly where
# a wheel runs. `libz.so.1` is the file every runtime actually ships, and dlopen
# finds it through the normal loader search path (ldconfig cache, LD_LIBRARY_PATH,
# default dirs). This was the real reason the CI wheel smoke test failed: the old
# preloader asked find_library("z"), got None, and skipped libz entirely.
_ZLIB_SONAMES = ["libz.so.1", "libz.so", "libz.1.dylib", "libz.dylib"]
_MPI_SONAMES = ["libmpi.so", "libmpi.so.40", "libmpi.so.12", "libmpi.dylib"]


def _preload_dependencies():
    """Preload under-declared shared dependencies (zlib, and MPI when parallel)
    RTLD_GLOBAL, before Scotch loads, so its calls resolve even under eager
    binding (-z now, the manylinux default). See the module comment above for
    why this is needed and why it is one of two independent layers of defense.
    Reuses _dlopen_system's find_library-then-soname search; a miss is a no-op
    (the library may already be global, or the bundled .so's NEEDED covers it)."""
    _dlopen_system("z", _ZLIB_SONAMES)
    if _PARALLEL:
        _dlopen_system("mpi", _MPI_SONAMES)


def _load_system_libraries():
    """Load Scotch from the system linker paths (distro/conda packages).

    System packages ship unsuffixed symbols and a single integer width;
    _detect_suffix() verifies the width matches PYSCOTCH_INT_SIZE.
    """
    _dlopen_system("scotcherr", ["libscotcherr.so", "libscotcherr.so.7", "libscotcherr-7.0.so"])

    seq = _dlopen_system("scotch", ["libscotch.so", "libscotch.so.7", "libscotch-7.0.so"])
    if seq is None:
        raise FileNotFoundError(
            "No Scotch library found. Either:\n"
            "  - run 'make build-all' in a PyScotch checkout,\n"
            "  - set PYSCOTCH_LIB_DIR to a directory containing libscotch.so,\n"
            "  - or install a system Scotch (e.g. 'apt install libscotch-dev', "
            "'conda install scotch')."
        )
    print(f"✓ Loaded system Scotch ({_INT_SIZE}-bit requested)", file=sys.stderr)

    par = None
    if _PARALLEL:
        par = _dlopen_system(
            "ptscotch", ["libptscotch.so", "libptscotch.so.7", "libptscotch-7.0.so"]
        )
        if par is None:
            raise FileNotFoundError(
                "No system PT-Scotch library found (PYSCOTCH_PARALLEL=1). "
                "Install it (e.g. 'apt install libptscotch-dev') or set "
                "PYSCOTCH_PARALLEL=0."
            )
        print("✓ Loaded system PT-Scotch", file=sys.stderr)

    return seq, par


# Handle to libpyscotch_compat.so when it provides error capture; None when
# running against a system Scotch (no shim, messages go to stderr as usual)
_err_capture = None


def _load_error_capture(lib_dir):
    """Load the compat shim FIRST and globally, so Scotch's calls to the
    deliberately-unsuffixed SCOTCH_errorPrint/W resolve to our capturing
    implementations instead of libscotcherr's stderr printers."""
    global _err_capture
    compat_path = lib_dir / "libpyscotch_compat.so"
    if not compat_path.exists():
        return
    try:
        handle = ctypes.CDLL(str(compat_path), mode=ctypes.RTLD_GLOBAL)
        handle.pyscotch_err_get.restype = c_char_p
        handle.pyscotch_err_get.argtypes = []
        handle.pyscotch_err_clear.restype = None
        handle.pyscotch_err_clear.argtypes = []
        _err_capture = handle
    except (OSError, AttributeError):
        pass  # older shim without error capture: keep stderr behavior


def get_scotch_messages(clear=True) -> str:
    """Error/warning messages Scotch emitted since the last clear.

    Empty string when capture is unavailable (system-Scotch mode) or when
    nothing was emitted. Messages may include warnings from earlier calls.
    """
    if _err_capture is None:
        return ""
    text = (_err_capture.pyscotch_err_get() or b"").decode("utf-8", "replace")
    if clear:
        _err_capture.pyscotch_err_clear()
    return text


def scotch_error(context: str, ret=None) -> RuntimeError:
    """Build a RuntimeError for a failed Scotch call, appending any captured
    Scotch error messages. Usage: `raise lib.scotch_error("SCOTCH_x failed", ret)`.
    """
    message = context if ret is None else f"{context} (error code: {ret})"
    captured = get_scotch_messages()
    if captured:
        message = f"{message}\n{captured}"
    return RuntimeError(message)


def _load_libraries():
    """Load the Scotch libraries."""
    lib_dir = _get_lib_dir()

    if lib_dir is None:
        return _load_system_libraries()

    # Error capture must be in the global symbol table before any Scotch
    # library binds SCOTCH_errorPrint
    _load_error_capture(lib_dir)

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

# Directory the libraries were loaded from (also used by graph.c_fopen to
# locate libpyscotch_compat.so built with the same toolchain).
# None means system-installed Scotch (c_fopen then uses the platform libc).
_loaded_lib_dir = _get_lib_dir()
_lib_dir = str(_loaded_lib_dir) if _loaded_lib_dir is not None else None

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


# Functions the library exports WITHOUT the _32/_64 suffix even though the
# suffixed headers declare them with one (upstream inconsistency in Scotch's
# SCOTCH_RENAME_ALL handling; they are int-size independent so this is safe).
_UNSUFFIXED_FUNCTIONS = {"SCOTCH_memFree"}


def _detect_suffix() -> str:
    """Detect whether the loaded library uses _32/_64 symbol suffixes.

    PyScotch's own builds compile Scotch with SCOTCH_NAME_SUFFIX, but system
    and conda-forge packages ship plain SCOTCH_* symbols. In the unsuffixed
    case, SCOTCH_numSizeof() must confirm the library's integer width matches
    PYSCOTCH_INT_SIZE — an unsuffixed library has exactly one width and
    loading it under the wrong one would corrupt every array we pass.
    """
    if hasattr(_lib_sequential, f"SCOTCH_graphInit_{_INT_SIZE}"):
        return f"_{_INT_SIZE}"
    if hasattr(_lib_sequential, "SCOTCH_graphInit"):
        try:
            sizeof_func = _lib_sequential.SCOTCH_numSizeof
        except AttributeError:
            raise RuntimeError(
                "Unsuffixed Scotch library lacks SCOTCH_numSizeof(); cannot "
                "verify its integer width. Scotch >= 7.0 is required."
            )
        sizeof_func.restype = c_int
        sizeof_func.argtypes = []
        lib_bits = sizeof_func() * 8
        if lib_bits != _INT_SIZE:
            raise RuntimeError(
                f"Loaded an unsuffixed Scotch library with {lib_bits}-bit "
                f"SCOTCH_Num, but PYSCOTCH_INT_SIZE={_INT_SIZE}. "
                f"Set PYSCOTCH_INT_SIZE={lib_bits} to use this library."
            )
        return ""
    raise RuntimeError(
        f"Loaded library exports neither SCOTCH_graphInit_{_INT_SIZE} nor "
        f"SCOTCH_graphInit — not a usable Scotch library."
    )


# Function-name prefixes (lowercased) of symbols exported by libptscotch.so:
# distributed graphs, parallel strategies and the distributed mapping/ordering
# opaque-structure helpers all live in the parallel library.
_PARALLEL_FUNC_PREFIXES = ("scotch_dgraph", "scotch_stratdgraph", "scotch_dmap", "scotch_dorder")


def _get_func(name: str):
    """Get a Scotch function with the correct suffix."""
    # PT-Scotch functions are in the parallel library
    if name.lower().startswith(_PARALLEL_FUNC_PREFIXES):
        if not _lib_parallel:
            raise AttributeError(
                f"{name} requires PT-Scotch (parallel variant). "
                f"Set PYSCOTCH_PARALLEL=1 to enable."
            )
        handle = _lib_parallel
    else:
        # All other SCOTCH_* functions are in the sequential library
        handle = _lib_sequential

    try:
        return getattr(handle, f"{name}{_SUFFIX}")
    except AttributeError:
        if name in _UNSUFFIXED_FUNCTIONS:
            return getattr(handle, name)
        raise


# Symbol suffix: "_32"/"_64" for PyScotch's own builds, "" for system or
# conda-forge Scotch packages (which are built without SCOTCH_NAME_SUFFIX)
_SUFFIX = _detect_suffix()


def _compute_structure_sizes():
    """Compute structure sizes using SCOTCH_*Sizeof() functions."""
    sizes = {}

    # Sequential structures (always available)
    sizes["graph"] = _get_func("SCOTCH_graphSizeof")()
    sizes["mesh"] = _get_func("SCOTCH_meshSizeof")()
    sizes["strat"] = _get_func("SCOTCH_stratSizeof")()
    sizes["arch"] = _get_func("SCOTCH_archSizeof")()
    sizes["mapping"] = _get_func("SCOTCH_mapSizeof")()
    sizes["ordering"] = _get_func("SCOTCH_orderSizeof")()
    sizes["geom"] = _get_func("SCOTCH_geomSizeof")()
    # SCOTCH_contextSizeof was added in Scotch 7.0.5. Older system/distro builds
    # (e.g. Debian's libscotch-7.0) export SCOTCH_contextInit/Exit but NOT the
    # sizeof accessor, so we can't learn the SCOTCH_Context struct size. Record
    # None here; import still works, and SCOTCH_Context is then defined as an
    # un-allocatable type (see below) rather than guessing a size and handing an
    # undersized buffer to the (present) SCOTCH_contextInit.
    try:
        sizes["context"] = _get_func("SCOTCH_contextSizeof")()
    except AttributeError:
        sizes["context"] = None

    # Parallel structures (only if parallel variant)
    if _lib_parallel:
        sizes["dgraph"] = _get_func("SCOTCH_dgraphSizeof")()
        sizes["dmapping"] = _get_func("SCOTCH_dmapSizeof")()
        sizes["dordering"] = _get_func("SCOTCH_dorderSizeof")()
    else:
        sizes["dgraph"] = None
        sizes["dmapping"] = None
        sizes["dordering"] = None

    return sizes


# Compute sizes and define structures
_SIZES = _compute_structure_sizes()

SCOTCH_Graph = _make_opaque_struct("SCOTCH_Graph", _SIZES["graph"])
SCOTCH_Mesh = _make_opaque_struct("SCOTCH_Mesh", _SIZES["mesh"])
SCOTCH_Strat = _make_opaque_struct("SCOTCH_Strat", _SIZES["strat"])
SCOTCH_Arch = _make_opaque_struct("SCOTCH_Arch", _SIZES["arch"])
SCOTCH_Mapping = _make_opaque_struct("SCOTCH_Mapping", _SIZES["mapping"])
SCOTCH_Ordering = _make_opaque_struct("SCOTCH_Ordering", _SIZES["ordering"])
SCOTCH_Geom = _make_opaque_struct("SCOTCH_Geom", _SIZES["geom"])
if _SIZES["context"] is not None:
    # Scotch >= 7.0.5: SCOTCH_contextSizeof gave us the real size.
    SCOTCH_Context = _make_opaque_struct("SCOTCH_Context", _SIZES["context"])
else:
    # Scotch < 7.0.5: no SCOTCH_contextSizeof, so the struct size is unknown.
    # The TYPE must still exist (POINTER() in signatures, imports, exports), but
    # it must be impossible to ALLOCATE — otherwise a wrongly-sized buffer could
    # reach the (present) SCOTCH_contextInit from ANY code path and overflow.
    # Enforce that at the type level rather than trusting one caller's guard.
    class SCOTCH_Context(Structure):
        _fields_ = [("_unavailable", ctypes.c_byte * 1)]

        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "SCOTCH_Context is unavailable: the loaded Scotch lacks "
                "SCOTCH_contextSizeof (added in Scotch 7.0.5), so its size is "
                "unknown and it cannot be allocated safely. Use the bundled "
                "wheel or conda Scotch, or upgrade the system Scotch to >= 7.0.5."
            )

    SCOTCH_Context.__qualname__ = "SCOTCH_Context"

if _SIZES["dgraph"]:
    SCOTCH_Dgraph = _make_opaque_struct("SCOTCH_Dgraph", _SIZES["dgraph"])
    SCOTCH_Dmapping = _make_opaque_struct("SCOTCH_Dmapping", _SIZES["dmapping"])
    SCOTCH_Dordering = _make_opaque_struct("SCOTCH_Dordering", _SIZES["dordering"])
else:
    SCOTCH_Dgraph = None
    SCOTCH_Dmapping = None
    SCOTCH_Dordering = None

print(
    f"✓ Structure sizes: graph={_SIZES['graph']}, strat={_SIZES['strat']}, "
    f"arch={_SIZES['arch']}, dgraph={_SIZES['dgraph']}",
    file=sys.stderr,
)

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
    ContextPtr = POINTER(SCOTCH_Context)
    OrderingPtr = POINTER(SCOTCH_Ordering)
    GeomPtr = POINTER(SCOTCH_Geom)
    NumPtr = POINTER(SCOTCH_Num)
    IdxPtr = POINTER(SCOTCH_Idx)

    bindings = {}

    # --- Graph functions ---
    bindings["SCOTCH_graphInit"] = (c_int, [GraphPtr])
    bindings["SCOTCH_graphExit"] = (None, [GraphPtr])
    bindings["SCOTCH_graphBuild"] = (
        c_int,
        [
            GraphPtr,
            SCOTCH_Num,
            SCOTCH_Num,
            NumPtr,
            NumPtr,
            NumPtr,
            NumPtr,
            SCOTCH_Num,
            NumPtr,
            NumPtr,
        ],
    )
    bindings["SCOTCH_graphCheck"] = (c_int, [GraphPtr])
    bindings["SCOTCH_graphSize"] = (None, [GraphPtr, NumPtr, NumPtr])
    bindings["SCOTCH_graphData"] = (
        None,
        [
            GraphPtr,
            NumPtr,
            NumPtr,
            POINTER(NumPtr),
            POINTER(NumPtr),
            POINTER(NumPtr),
            POINTER(NumPtr),
            NumPtr,
            POINTER(NumPtr),
            POINTER(NumPtr),
        ],
    )
    bindings["SCOTCH_graphLoad"] = (c_int, [GraphPtr, c_void_p, SCOTCH_Num, SCOTCH_Num])
    bindings["SCOTCH_graphSave"] = (c_int, [GraphPtr, c_void_p])
    bindings["SCOTCH_graphBase"] = (SCOTCH_Num, [GraphPtr, SCOTCH_Num])
    bindings["SCOTCH_graphPart"] = (c_int, [GraphPtr, SCOTCH_Num, StratPtr, NumPtr])
    bindings["SCOTCH_graphPartOvl"] = (c_int, [GraphPtr, SCOTCH_Num, StratPtr, NumPtr])
    bindings["SCOTCH_graphPartFixed"] = (c_int, [GraphPtr, SCOTCH_Num, StratPtr, NumPtr])
    bindings["SCOTCH_graphOrder"] = (
        c_int,
        [GraphPtr, StratPtr, NumPtr, NumPtr, NumPtr, NumPtr, NumPtr],
    )
    bindings["SCOTCH_graphCoarsen"] = (
        c_int,
        [GraphPtr, SCOTCH_Num, c_double, SCOTCH_Num, GraphPtr, NumPtr],
    )
    bindings["SCOTCH_graphCoarsenMatch"] = (c_int, [GraphPtr, NumPtr, c_double, SCOTCH_Num, NumPtr])
    bindings["SCOTCH_graphCoarsenBuild"] = (c_int, [GraphPtr, SCOTCH_Num, NumPtr, GraphPtr, NumPtr])
    bindings["SCOTCH_graphInduceList"] = (c_int, [GraphPtr, SCOTCH_Num, NumPtr, GraphPtr])
    bindings["SCOTCH_graphInducePart"] = (
        c_int,
        [GraphPtr, SCOTCH_Num, POINTER(SCOTCH_GraphPart2), SCOTCH_GraphPart2, GraphPtr],
    )
    bindings["SCOTCH_graphDiamPV"] = (SCOTCH_Num, [GraphPtr])
    bindings["SCOTCH_graphColor"] = (c_int, [GraphPtr, NumPtr, NumPtr, SCOTCH_Num])
    bindings["SCOTCH_graphStat"] = (
        None,
        [
            GraphPtr,
            NumPtr,
            NumPtr,
            NumPtr,
            POINTER(c_double),
            POINTER(c_double),
            NumPtr,
            NumPtr,
            POINTER(c_double),
            POINTER(c_double),
            NumPtr,
            NumPtr,
            NumPtr,
            POINTER(c_double),
            POINTER(c_double),
        ],
    )
    bindings["SCOTCH_graphMap"] = (c_int, [GraphPtr, ArchPtr, StratPtr, NumPtr])
    bindings["SCOTCH_graphMapInit"] = (c_int, [GraphPtr, MappingPtr, ArchPtr, NumPtr])
    bindings["SCOTCH_graphMapExit"] = (None, [GraphPtr, MappingPtr])
    bindings["SCOTCH_graphMapCompute"] = (c_int, [GraphPtr, MappingPtr, StratPtr])
    bindings["SCOTCH_graphRemapCompute"] = (
        c_int,
        [GraphPtr, MappingPtr, MappingPtr, c_double, NumPtr, StratPtr],
    )
    bindings["SCOTCH_graphMapFixed"] = (c_int, [GraphPtr, ArchPtr, StratPtr, NumPtr])
    bindings["SCOTCH_graphMapFixedCompute"] = (c_int, [GraphPtr, MappingPtr, StratPtr])
    bindings["SCOTCH_graphMapLoad"] = (c_int, [GraphPtr, MappingPtr, c_void_p])
    bindings["SCOTCH_graphMapSave"] = (c_int, [GraphPtr, MappingPtr, c_void_p])
    bindings["SCOTCH_graphMapView"] = (c_int, [GraphPtr, MappingPtr, c_void_p])
    bindings["SCOTCH_graphRemap"] = (
        c_int,
        [GraphPtr, ArchPtr, NumPtr, c_double, NumPtr, StratPtr, NumPtr],
    )
    bindings["SCOTCH_graphRemapFixed"] = (
        c_int,
        [GraphPtr, ArchPtr, NumPtr, c_double, NumPtr, StratPtr, NumPtr],
    )
    bindings["SCOTCH_graphRemapFixedCompute"] = (
        c_int,
        [GraphPtr, MappingPtr, MappingPtr, c_double, NumPtr, StratPtr],
    )
    bindings["SCOTCH_graphRepart"] = (
        c_int,
        [GraphPtr, SCOTCH_Num, NumPtr, c_double, NumPtr, StratPtr, NumPtr],
    )
    bindings["SCOTCH_graphRepartFixed"] = (
        c_int,
        [GraphPtr, SCOTCH_Num, NumPtr, c_double, NumPtr, StratPtr, NumPtr],
    )
    bindings["SCOTCH_graphPartOvlView"] = (c_int, [GraphPtr, SCOTCH_Num, NumPtr, c_void_p])
    bindings["SCOTCH_graphFree"] = (None, [GraphPtr])
    bindings["SCOTCH_graphDump"] = (c_int, [GraphPtr, c_char_p, c_char_p, c_void_p])
    bindings["SCOTCH_graphTabLoad"] = (c_int, [GraphPtr, NumPtr, c_void_p])
    bindings["SCOTCH_graphTabSave"] = (c_int, [GraphPtr, NumPtr, c_void_p])

    # --- Graph ordering (low-level) ---
    bindings["SCOTCH_graphOrderInit"] = (
        c_int,
        [GraphPtr, OrderingPtr, NumPtr, NumPtr, NumPtr, NumPtr, NumPtr],
    )
    bindings["SCOTCH_graphOrderExit"] = (None, [GraphPtr, OrderingPtr])
    bindings["SCOTCH_graphOrderLoad"] = (c_int, [GraphPtr, OrderingPtr, c_void_p])
    bindings["SCOTCH_graphOrderSave"] = (c_int, [GraphPtr, OrderingPtr, c_void_p])
    bindings["SCOTCH_graphOrderSaveMap"] = (c_int, [GraphPtr, OrderingPtr, c_void_p])
    bindings["SCOTCH_graphOrderSaveTree"] = (c_int, [GraphPtr, OrderingPtr, c_void_p])
    bindings["SCOTCH_graphOrderCompute"] = (c_int, [GraphPtr, OrderingPtr, StratPtr])
    bindings["SCOTCH_graphOrderComputeList"] = (
        c_int,
        [GraphPtr, OrderingPtr, SCOTCH_Num, NumPtr, StratPtr],
    )
    bindings["SCOTCH_graphOrderCheck"] = (c_int, [GraphPtr, OrderingPtr])
    bindings["SCOTCH_graphOrderList"] = (
        c_int,
        [GraphPtr, SCOTCH_Num, NumPtr, StratPtr, NumPtr, NumPtr, NumPtr, NumPtr, NumPtr],
    )

    # --- Graph geometry I/O ---
    bindings["SCOTCH_graphGeomLoadScot"] = (
        c_int,
        [GraphPtr, GeomPtr, c_void_p, c_void_p, c_char_p],
    )
    bindings["SCOTCH_graphGeomLoadChac"] = (
        c_int,
        [GraphPtr, GeomPtr, c_void_p, c_void_p, c_char_p],
    )
    bindings["SCOTCH_graphGeomLoadHabo"] = (
        c_int,
        [GraphPtr, GeomPtr, c_void_p, c_void_p, c_char_p],
    )
    bindings["SCOTCH_graphGeomLoadMmkt"] = (
        c_int,
        [GraphPtr, GeomPtr, c_void_p, c_void_p, c_char_p],
    )
    bindings["SCOTCH_graphGeomSaveScot"] = (
        c_int,
        [GraphPtr, GeomPtr, c_void_p, c_void_p, c_char_p],
    )
    bindings["SCOTCH_graphGeomSaveChac"] = (
        c_int,
        [GraphPtr, GeomPtr, c_void_p, c_void_p, c_char_p],
    )
    bindings["SCOTCH_graphGeomSaveMmkt"] = (
        c_int,
        [GraphPtr, GeomPtr, c_void_p, c_void_p, c_char_p],
    )

    # --- Strategy functions ---
    bindings["SCOTCH_stratInit"] = (c_int, [StratPtr])
    bindings["SCOTCH_stratExit"] = (None, [StratPtr])
    bindings["SCOTCH_stratGraphMap"] = (c_int, [StratPtr, c_char_p])
    bindings["SCOTCH_stratGraphMapBuild"] = (c_int, [StratPtr, SCOTCH_Num, SCOTCH_Num, c_double])
    bindings["SCOTCH_stratGraphOrder"] = (c_int, [StratPtr, c_char_p])
    bindings["SCOTCH_stratGraphOrderBuild"] = (c_int, [StratPtr, SCOTCH_Num, SCOTCH_Num, c_double])
    bindings["SCOTCH_stratGraphPartOvl"] = (c_int, [StratPtr, c_char_p])
    bindings["SCOTCH_stratGraphPartOvlBuild"] = (
        c_int,
        [StratPtr, SCOTCH_Num, SCOTCH_Num, c_double],
    )
    bindings["SCOTCH_stratGraphBipart"] = (c_int, [StratPtr, c_char_p])
    bindings["SCOTCH_stratGraphClusterBuild"] = (
        c_int,
        [StratPtr, SCOTCH_Num, SCOTCH_Num, c_double, c_double],
    )
    bindings["SCOTCH_stratMeshOrder"] = (c_int, [StratPtr, c_char_p])
    bindings["SCOTCH_stratMeshOrderBuild"] = (c_int, [StratPtr, SCOTCH_Num, c_double])
    bindings["SCOTCH_stratSave"] = (c_int, [StratPtr, c_void_p])

    # --- Architecture functions ---
    bindings["SCOTCH_archInit"] = (c_int, [ArchPtr])
    bindings["SCOTCH_archExit"] = (None, [ArchPtr])
    bindings["SCOTCH_archCmplt"] = (c_int, [ArchPtr, SCOTCH_Num])
    bindings["SCOTCH_archCmpltw"] = (c_int, [ArchPtr, SCOTCH_Num, NumPtr])
    bindings["SCOTCH_archBuild0"] = (c_int, [ArchPtr, GraphPtr, SCOTCH_Num, NumPtr, StratPtr])
    bindings["SCOTCH_archBuild2"] = (c_int, [ArchPtr, GraphPtr, SCOTCH_Num, NumPtr])
    bindings["SCOTCH_archSub"] = (c_int, [ArchPtr, ArchPtr, SCOTCH_Num, NumPtr])
    bindings["SCOTCH_archLoad"] = (c_int, [ArchPtr, c_void_p])
    bindings["SCOTCH_archSave"] = (c_int, [ArchPtr, c_void_p])
    bindings["SCOTCH_archSize"] = (SCOTCH_Num, [ArchPtr])
    bindings["SCOTCH_archName"] = (c_char_p, [ArchPtr])
    bindings["SCOTCH_archVar"] = (c_int, [ArchPtr])
    bindings["SCOTCH_archBuild"] = (c_int, [ArchPtr, GraphPtr, SCOTCH_Num, NumPtr, StratPtr])
    bindings["SCOTCH_archHcub"] = (c_int, [ArchPtr, SCOTCH_Num])
    bindings["SCOTCH_archMesh2"] = (c_int, [ArchPtr, SCOTCH_Num, SCOTCH_Num])
    bindings["SCOTCH_archMesh3"] = (c_int, [ArchPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num])
    bindings["SCOTCH_archMeshX"] = (c_int, [ArchPtr, SCOTCH_Num, NumPtr])
    bindings["SCOTCH_archTleaf"] = (c_int, [ArchPtr, SCOTCH_Num, NumPtr, NumPtr])
    bindings["SCOTCH_archTorus2"] = (c_int, [ArchPtr, SCOTCH_Num, SCOTCH_Num])
    bindings["SCOTCH_archTorus3"] = (c_int, [ArchPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num])
    bindings["SCOTCH_archTorusX"] = (c_int, [ArchPtr, SCOTCH_Num, NumPtr])
    bindings["SCOTCH_archVcmplt"] = (c_int, [ArchPtr])
    bindings["SCOTCH_archVhcub"] = (c_int, [ArchPtr])

    # --- Mesh functions ---
    bindings["SCOTCH_meshInit"] = (c_int, [MeshPtr])
    bindings["SCOTCH_meshExit"] = (None, [MeshPtr])
    bindings["SCOTCH_meshLoad"] = (c_int, [MeshPtr, c_void_p, SCOTCH_Num])
    bindings["SCOTCH_meshSave"] = (c_int, [MeshPtr, c_void_p])
    bindings["SCOTCH_meshCheck"] = (c_int, [MeshPtr])
    bindings["SCOTCH_meshBuild"] = (
        c_int,
        [
            MeshPtr,
            SCOTCH_Num,
            SCOTCH_Num,
            SCOTCH_Num,
            SCOTCH_Num,
            NumPtr,
            NumPtr,
            NumPtr,
            NumPtr,
            NumPtr,
            SCOTCH_Num,
            NumPtr,
        ],
    )
    bindings["SCOTCH_meshGraph"] = (c_int, [MeshPtr, GraphPtr])
    bindings["SCOTCH_meshSize"] = (None, [MeshPtr, NumPtr, NumPtr, NumPtr])
    bindings["SCOTCH_meshData"] = (
        None,
        [
            MeshPtr,
            NumPtr,
            NumPtr,
            NumPtr,
            NumPtr,
            POINTER(NumPtr),
            POINTER(NumPtr),
            POINTER(NumPtr),
            POINTER(NumPtr),
            POINTER(NumPtr),
            NumPtr,
            POINTER(NumPtr),
            NumPtr,
        ],
    )
    bindings["SCOTCH_meshGraph"] = (c_int, [MeshPtr, GraphPtr])
    bindings["SCOTCH_meshGraphDual"] = (c_int, [MeshPtr, GraphPtr, SCOTCH_Num])
    bindings["SCOTCH_meshStat"] = (
        None,
        [
            MeshPtr,
            NumPtr,
            NumPtr,
            NumPtr,
            POINTER(c_double),
            POINTER(c_double),
            NumPtr,
            NumPtr,
            POINTER(c_double),
            POINTER(c_double),
            NumPtr,
            NumPtr,
            POINTER(c_double),
            POINTER(c_double),
        ],
    )
    bindings["SCOTCH_meshOrder"] = (
        c_int,
        [MeshPtr, StratPtr, NumPtr, NumPtr, NumPtr, NumPtr, NumPtr],
    )
    bindings["SCOTCH_meshOrderInit"] = (
        c_int,
        [MeshPtr, OrderingPtr, NumPtr, NumPtr, NumPtr, NumPtr, NumPtr],
    )
    bindings["SCOTCH_meshOrderExit"] = (None, [MeshPtr, OrderingPtr])
    bindings["SCOTCH_meshOrderSave"] = (c_int, [MeshPtr, OrderingPtr, c_void_p])
    bindings["SCOTCH_meshOrderSaveMap"] = (c_int, [MeshPtr, OrderingPtr, c_void_p])
    bindings["SCOTCH_meshOrderSaveTree"] = (c_int, [MeshPtr, OrderingPtr, c_void_p])
    bindings["SCOTCH_meshOrderCompute"] = (c_int, [MeshPtr, OrderingPtr, StratPtr])
    bindings["SCOTCH_meshOrderCheck"] = (c_int, [MeshPtr, OrderingPtr])

    # --- Geometry functions ---
    bindings["SCOTCH_geomInit"] = (c_int, [GeomPtr])
    bindings["SCOTCH_geomExit"] = (None, [GeomPtr])
    bindings["SCOTCH_geomData"] = (None, [GeomPtr, NumPtr, POINTER(POINTER(c_double))])

    # --- Random functions ---
    bindings["SCOTCH_randomReset"] = (None, [])
    bindings["SCOTCH_randomSeed"] = (None, [SCOTCH_Num])
    bindings["SCOTCH_randomVal"] = (SCOTCH_Num, [SCOTCH_Num])
    bindings["SCOTCH_randomProc"] = (None, [c_int])
    bindings["SCOTCH_randomSave"] = (c_int, [c_void_p])
    bindings["SCOTCH_randomLoad"] = (c_int, [c_void_p])

    # --- Memory functions ---
    bindings["SCOTCH_memCur"] = (SCOTCH_Idx, [])
    bindings["SCOTCH_memMax"] = (SCOTCH_Idx, [])
    bindings["SCOTCH_memFree"] = (None, [c_void_p])

    # --- Context functions ---
    bindings["SCOTCH_contextInit"] = (c_int, [ContextPtr])
    bindings["SCOTCH_contextExit"] = (None, [ContextPtr])
    bindings["SCOTCH_contextOptionGetNum"] = (c_int, [ContextPtr, c_int, NumPtr])
    bindings["SCOTCH_contextOptionSetNum"] = (c_int, [ContextPtr, c_int, SCOTCH_Num])
    bindings["SCOTCH_contextRandomClone"] = (c_int, [ContextPtr])
    bindings["SCOTCH_contextRandomReset"] = (None, [ContextPtr])
    bindings["SCOTCH_contextRandomSeed"] = (None, [ContextPtr, SCOTCH_Num])
    bindings["SCOTCH_contextBindGraph"] = (c_int, [ContextPtr, GraphPtr, GraphPtr])
    bindings["SCOTCH_contextBindMesh"] = (c_int, [ContextPtr, MeshPtr, MeshPtr])

    # --- Version function ---
    # Takes plain int*, not SCOTCH_Num*
    bindings["SCOTCH_version"] = (None, [POINTER(c_int), POINTER(c_int), POINTER(c_int)])

    # Apply bindings
    missing = []
    for name, (restype, argtypes) in bindings.items():
        try:
            func = _get_func(name)
            func.restype = restype
            func.argtypes = argtypes
        except AttributeError:
            missing.append(name)  # Function may not exist in all versions

    # --- Dgraph functions (parallel only) ---
    if _lib_parallel:
        DgraphPtr = POINTER(SCOTCH_Dgraph)

        dgraph_bindings = {
            "SCOTCH_dgraphInit": (c_int, [DgraphPtr, c_void_p]),  # MPI_Comm as void*
            "SCOTCH_dgraphExit": (None, [DgraphPtr]),
            "SCOTCH_dgraphBuild": (
                c_int,
                [
                    DgraphPtr,
                    SCOTCH_Num,
                    SCOTCH_Num,
                    SCOTCH_Num,
                    NumPtr,
                    NumPtr,
                    NumPtr,
                    NumPtr,  # vertloctab, vendloctab, veloloctab, vlblloctab
                    SCOTCH_Num,
                    SCOTCH_Num,
                    NumPtr,
                    NumPtr,
                    NumPtr,  # edgelocnbr, edgelocsiz, edgeloctab, edgegsttab, edloloctab
                ],
            ),
            "SCOTCH_dgraphCheck": (c_int, [DgraphPtr]),
            "SCOTCH_dgraphData": (
                None,
                [
                    DgraphPtr,
                    NumPtr,
                    NumPtr,
                    NumPtr,
                    NumPtr,
                    NumPtr,  # baseval, vertglbnbr, vertlocnbr, vertlocmax, vertgstnbr
                    POINTER(NumPtr),
                    POINTER(NumPtr),
                    POINTER(NumPtr),
                    POINTER(NumPtr),  # vertloctab, vendloctab, veloloctab, vlblloctab
                    NumPtr,
                    NumPtr,
                    NumPtr,  # edgeglbnbr, edgelocnbr, edgelocsiz
                    POINTER(NumPtr),
                    POINTER(NumPtr),
                    POINTER(NumPtr),  # edgeloctab, edgegsttab, edloloctab
                    c_void_p,  # MPI_Comm*
                ],
            ),
            "SCOTCH_dgraphLoad": (c_int, [DgraphPtr, c_void_p, SCOTCH_Num, SCOTCH_Num]),
            "SCOTCH_dgraphSave": (c_int, [DgraphPtr, c_void_p]),
            "SCOTCH_dgraphCoarsen": (
                c_int,
                [DgraphPtr, SCOTCH_Num, c_double, SCOTCH_Num, DgraphPtr, NumPtr],
            ),
            "SCOTCH_dgraphCoarsenVertLocMax": (SCOTCH_Num, [DgraphPtr, SCOTCH_Num]),
            "SCOTCH_dgraphGhst": (c_int, [DgraphPtr]),
            "SCOTCH_dgraphGrow": (c_int, [DgraphPtr, SCOTCH_Num, NumPtr, SCOTCH_Num, NumPtr]),
            "SCOTCH_dgraphBand": (c_int, [DgraphPtr, SCOTCH_Num, NumPtr, SCOTCH_Num, DgraphPtr]),
            "SCOTCH_dgraphRedist": (
                c_int,
                [DgraphPtr, NumPtr, NumPtr, SCOTCH_Num, SCOTCH_Num, DgraphPtr],
            ),
            "SCOTCH_dgraphInducePart": (
                c_int,
                [DgraphPtr, NumPtr, SCOTCH_Num, SCOTCH_Num, DgraphPtr],
            ),
            "SCOTCH_dgraphFree": (None, [DgraphPtr]),
            "SCOTCH_dgraphBuildGrid3D": (
                c_int,
                [DgraphPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num],
            ),
            "SCOTCH_dgraphStat": (
                c_int,
                [
                    DgraphPtr,
                    NumPtr,
                    NumPtr,
                    NumPtr,  # velomin, velomax, velosum
                    POINTER(c_double),
                    POINTER(c_double),  # veloavg, velodlt
                    NumPtr,
                    NumPtr,  # degrmin, degrmax
                    POINTER(c_double),
                    POINTER(c_double),  # degravg, degrdlt
                    NumPtr,
                    NumPtr,
                    NumPtr,  # edlomin, edlomax, edlosum
                    POINTER(c_double),
                    POINTER(c_double),  # edloavg, edlodlt
                ],
            ),
            # Centralized <-> distributed conversion (SCOTCH_Graph on root rank)
            "SCOTCH_dgraphGather": (c_int, [DgraphPtr, GraphPtr]),
            "SCOTCH_dgraphScatter": (c_int, [DgraphPtr, GraphPtr]),
            # Distributed partitioning/mapping (one-shot entry points)
            "SCOTCH_dgraphPart": (c_int, [DgraphPtr, SCOTCH_Num, StratPtr, NumPtr]),
            "SCOTCH_dgraphMap": (c_int, [DgraphPtr, ArchPtr, StratPtr, NumPtr]),
            # Centralized ordering gathered from a distributed one (root rank)
            "SCOTCH_dgraphCorderInit": (
                c_int,
                [DgraphPtr, OrderingPtr, NumPtr, NumPtr, NumPtr, NumPtr, NumPtr],
            ),
            "SCOTCH_dgraphCorderExit": (None, [DgraphPtr, OrderingPtr]),
            # Parallel strategies (exported by libptscotch, not libscotch)
            "SCOTCH_stratDgraphMap": (c_int, [StratPtr, c_char_p]),
            "SCOTCH_stratDgraphMapBuild": (
                c_int,
                [StratPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, c_double],
            ),
            "SCOTCH_stratDgraphClusterBuild": (
                c_int,
                [StratPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, c_double, c_double],
            ),
            "SCOTCH_stratDgraphOrder": (c_int, [StratPtr, c_char_p]),
            "SCOTCH_stratDgraphOrderBuild": (
                c_int,
                [StratPtr, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, c_double],
            ),
        }

        # Bindings whose prototypes involve SCOTCH_Dmapping/SCOTCH_Dordering,
        # copied verbatim from ptscotch.h (FILE* -> c_void_p).
        DmappingPtr = POINTER(SCOTCH_Dmapping)
        DorderingPtr = POINTER(SCOTCH_Dordering)

        dgraph_bindings |= {
            "SCOTCH_dgraphMapInit": (c_int, [DgraphPtr, DmappingPtr, ArchPtr, NumPtr]),
            "SCOTCH_dgraphMapExit": (None, [DgraphPtr, DmappingPtr]),
            "SCOTCH_dgraphMapCompute": (c_int, [DgraphPtr, DmappingPtr, StratPtr]),
            "SCOTCH_dgraphMapSave": (c_int, [DgraphPtr, DmappingPtr, c_void_p]),
            "SCOTCH_dgraphMapView": (c_int, [DgraphPtr, DmappingPtr, c_void_p]),
            "SCOTCH_dgraphOrderInit": (c_int, [DgraphPtr, DorderingPtr]),
            "SCOTCH_dgraphOrderExit": (None, [DgraphPtr, DorderingPtr]),
            "SCOTCH_dgraphOrderCompute": (c_int, [DgraphPtr, DorderingPtr, StratPtr]),
            "SCOTCH_dgraphOrderComputeList": (
                c_int,
                [DgraphPtr, DorderingPtr, SCOTCH_Num, NumPtr, StratPtr],
            ),
            "SCOTCH_dgraphOrderPerm": (c_int, [DgraphPtr, DorderingPtr, NumPtr]),
            "SCOTCH_dgraphOrderCblkDist": (SCOTCH_Num, [DgraphPtr, DorderingPtr]),
            "SCOTCH_dgraphOrderTreeDist": (c_int, [DgraphPtr, DorderingPtr, NumPtr, NumPtr]),
            "SCOTCH_dgraphOrderSave": (c_int, [DgraphPtr, DorderingPtr, c_void_p]),
            "SCOTCH_dgraphOrderSaveMap": (c_int, [DgraphPtr, DorderingPtr, c_void_p]),
            "SCOTCH_dgraphOrderSaveTree": (c_int, [DgraphPtr, DorderingPtr, c_void_p]),
            "SCOTCH_dgraphOrderGather": (c_int, [DgraphPtr, DorderingPtr, OrderingPtr]),
        }

        for name, (restype, argtypes) in dgraph_bindings.items():
            try:
                func = _get_func(name)
                func.restype = restype
                func.argtypes = argtypes
            except AttributeError:
                missing.append(name)

        bindings.update(dgraph_bindings)

    return bindings, missing


# Bind all functions.
# _DECLARED_BINDINGS maps C function name -> (restype, argtypes) as declared
# above; _MISSING_BINDINGS lists declared functions absent from the loaded
# libraries. Both are introspected by the signature-verification tests.
_DECLARED_BINDINGS, _MISSING_BINDINGS = _bind_functions()

# =============================================================================
# Public API
# =============================================================================


@internal_api
def get_scotch_int_size() -> int:
    """Return the SCOTCH_Num size in bits (32 or 64)."""
    return _INT_SIZE


@internal_api
def get_scotch_dtype():
    """Return the numpy dtype corresponding to SCOTCH_Num."""
    import numpy as np

    return np.int32 if _INT_SIZE == 32 else np.int64


def to_scotch_array(array, copy=False):
    """Convert a numpy array to the correct Scotch dtype and return (array, ctypes_ptr).

    The returned array must be kept alive for the pointer to remain valid.
    """
    arr = np.asarray(array, dtype=get_scotch_dtype())
    if copy:
        arr = arr.copy()
    return arr, arr.ctypes.data_as(POINTER(SCOTCH_Num))


def to_scotch_array_optional(array):
    """Like to_scotch_array but accepts None, returning (None, None)."""
    if array is None:
        return None, None
    return to_scotch_array(array)


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
    "to_scotch_array",
    "to_scotch_array_optional",
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
    "SCOTCH_Context",
    "SCOTCH_Dgraph",
    "SCOTCH_Dmapping",
    "SCOTCH_Dordering",
    # Constants
    "SCOTCH_COARSENNONE",
    "SCOTCH_COARSENFOLD",
    "SCOTCH_COARSENFOLDDUP",
    "SCOTCH_COARSENNOMERGE",
    "SCOTCH_DGRAPHBUILDGRID3DGRID",
    "SCOTCH_DGRAPHBUILDGRID3DTORUS",
    "SCOTCH_DGRAPHBUILDGRID3DNGB6",
    "SCOTCH_DGRAPHBUILDGRID3DNGB26",
    "SCOTCH_DGRAPHBUILDGRID3DVERTLOAD",
    "SCOTCH_DGRAPHBUILDGRID3DEDGELOAD",
]
