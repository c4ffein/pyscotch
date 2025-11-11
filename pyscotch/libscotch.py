"""
Low-level ctypes bindings to the PT-Scotch C library.

Multi-Variant Support:
This module can load multiple Scotch variants simultaneously (32-bit/64-bit × sequential/parallel)
and switch between them at runtime without reloading.
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
from typing import Optional, Tuple, Dict

# Constants
_OPAQUE_STRUCTURE_SIZE = 256


# Opaque structure types (shared across all variants)
class SCOTCH_Graph(Structure):
    """Opaque graph structure."""
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]

class SCOTCH_Mesh(Structure):
    """Opaque mesh structure."""
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]

class SCOTCH_Strat(Structure):
    """Opaque strategy structure."""
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]

class SCOTCH_Arch(Structure):
    """Opaque architecture structure."""
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]

class SCOTCH_Mapping(Structure):
    """Opaque mapping structure."""
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]

class SCOTCH_Ordering(Structure):
    """Opaque ordering structure."""
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]

class SCOTCH_Geom(Structure):
    """Opaque geometry structure."""
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]


class ScotchVariant:
    """
    Encapsulates a single Scotch library variant.

    Each variant has its own isolated library handles and can coexist
    with other variants in the same process.
    """

    def __init__(self, int_size: int, parallel: bool, lib_dir: Path, header_dir: Path):
        """
        Initialize a Scotch variant.

        Args:
            int_size: 32 or 64
            parallel: True for PT-Scotch, False for sequential
            lib_dir: Directory containing the libraries
            header_dir: Directory containing headers
        """
        self.int_size = int_size
        self.parallel = parallel
        self.lib_dir = Path(lib_dir)
        self.header_dir = Path(header_dir)

        # Type definitions for this variant
        self.SCOTCH_Num = c_long if int_size == 64 else c_int
        self.SCOTCH_Idx = c_long if int_size == 64 else c_int

        # Library handles (loaded with RTLD_LOCAL for isolation)
        self._libscotch = None
        self._libscotcherr = None

        # Function pointers (will be set during loading)
        self.functions = {}

        self._load_libraries()
        self._bind_functions()

    def _load_libraries(self):
        """Load the library files with RTLD_LOCAL for isolation."""
        try:
            # Preload zlib globally (shared dependency)
            try:
                zlib_path = ctypes.util.find_library('z')
                if zlib_path and not hasattr(self.__class__, '_zlib_loaded'):
                    ctypes.CDLL(zlib_path, mode=ctypes.RTLD_GLOBAL)
                    self.__class__._zlib_loaded = True
            except (OSError, AttributeError, TypeError):
                pass

            # Preload MPI globally if building PT-Scotch (parallel variant)
            if self.parallel and not hasattr(self.__class__, '_mpi_loaded'):
                try:
                    # Try to load the MPI library globally
                    mpi_path = ctypes.util.find_library('mpi')
                    if mpi_path:
                        ctypes.CDLL(mpi_path, mode=ctypes.RTLD_GLOBAL)
                        self.__class__._mpi_loaded = True
                except (OSError, AttributeError, TypeError):
                    pass

            # Load error library globally (shared across all variants - it's identical)
            # We only need to load it once, all variants can use the same instance
            if not hasattr(self.__class__, '_scotcherr_loaded'):
                err_lib_path = self.lib_dir / "libscotcherr.so"
                if err_lib_path.exists():
                    try:
                        # RTLD_GLOBAL = shared namespace (safe because libscotcherr is identical for all variants)
                        self._libscotcherr = ctypes.CDLL(str(err_lib_path), mode=ctypes.RTLD_GLOBAL)
                        self.__class__._scotcherr_loaded = True
                    except OSError as e:
                        print(f"Warning: Could not load {err_lib_path}: {e}", file=sys.stderr)

            # With suffixes, all variants can coexist in the same namespace
            # PT-Scotch depends on sequential scotch symbols, so we need RTLD_GLOBAL

            # For parallel variants, first load sequential scotch globally
            if self.parallel:
                seq_lib_path = self.lib_dir / "libscotch.so"
                if not seq_lib_path.exists():
                    raise FileNotFoundError(f"Sequential library required for PT-Scotch: {seq_lib_path}")
                # Load sequential scotch globally so PT-Scotch can access its symbols
                ctypes.CDLL(str(seq_lib_path), mode=ctypes.RTLD_GLOBAL)

            # Determine main library name
            lib_name = "libptscotch.so" if self.parallel else "libscotch.so"
            lib_path = self.lib_dir / lib_name

            if not lib_path.exists():
                raise FileNotFoundError(f"Library not found: {lib_path}")

            # Load main library with RTLD_GLOBAL (safe with suffixes - no collisions)
            self._libscotch = ctypes.CDLL(str(lib_path), mode=ctypes.RTLD_GLOBAL)

            print(f"✓ Loaded Scotch variant: {self.int_size}-bit, "
                  f"{'parallel' if self.parallel else 'sequential'} from {lib_path}",
                  file=sys.stderr)

        except Exception as e:
            print(f"✗ Failed to load Scotch variant ({self.int_size}-bit, "
                  f"{'parallel' if self.parallel else 'sequential'}): {e}",
                  file=sys.stderr)
            self._libscotch = None

    def _get_func(self, name):
        """Get a Scotch function with the correct suffix."""
        suffixed_name = f"{name}_{self.int_size}"
        return getattr(self._libscotch, suffixed_name)

    def _bind_functions(self):
        """Bind Scotch C functions to this variant."""
        if not self._libscotch:
            return

        try:
            lib = self._libscotch

            # Graph functions
            self.SCOTCH_graphInit = self._get_func("SCOTCH_graphInit")
            self.SCOTCH_graphInit.argtypes = [POINTER(SCOTCH_Graph)]
            self.SCOTCH_graphInit.restype = c_int

            self.SCOTCH_graphExit = self._get_func("SCOTCH_graphExit")
            self.SCOTCH_graphExit.argtypes = [POINTER(SCOTCH_Graph)]
            self.SCOTCH_graphExit.restype = None

            self.SCOTCH_graphBuild = self._get_func("SCOTCH_graphBuild")
            self.SCOTCH_graphBuild.argtypes = [
                POINTER(SCOTCH_Graph),
                self.SCOTCH_Num,  # baseval
                self.SCOTCH_Num,  # vertnbr
                POINTER(self.SCOTCH_Num),  # verttab
                POINTER(self.SCOTCH_Num),  # vendtab
                POINTER(self.SCOTCH_Num),  # velotab
                POINTER(self.SCOTCH_Num),  # vlbltab
                self.SCOTCH_Num,  # edgenbr
                POINTER(self.SCOTCH_Num),  # edgetab
                POINTER(self.SCOTCH_Num),  # edlotab
            ]
            self.SCOTCH_graphBuild.restype = c_int

            self.SCOTCH_graphCheck = self._get_func("SCOTCH_graphCheck")
            self.SCOTCH_graphCheck.argtypes = [POINTER(SCOTCH_Graph)]
            self.SCOTCH_graphCheck.restype = c_int

            self.SCOTCH_graphSize = self._get_func("SCOTCH_graphSize")
            self.SCOTCH_graphSize.argtypes = [
                POINTER(SCOTCH_Graph),
                POINTER(self.SCOTCH_Num),
                POINTER(self.SCOTCH_Num),
            ]
            self.SCOTCH_graphSize.restype = None

            self.SCOTCH_graphPart = self._get_func("SCOTCH_graphPart")
            self.SCOTCH_graphPart.argtypes = [
                POINTER(SCOTCH_Graph),
                self.SCOTCH_Num,
                POINTER(SCOTCH_Strat),
                POINTER(self.SCOTCH_Num),
            ]
            self.SCOTCH_graphPart.restype = c_int

            self.SCOTCH_graphOrder = self._get_func("SCOTCH_graphOrder")
            self.SCOTCH_graphOrder.argtypes = [
                POINTER(SCOTCH_Graph),
                POINTER(SCOTCH_Strat),
                POINTER(self.SCOTCH_Num),
                POINTER(self.SCOTCH_Num),
                POINTER(self.SCOTCH_Num),
                POINTER(self.SCOTCH_Num),
                POINTER(self.SCOTCH_Num),
            ]
            self.SCOTCH_graphOrder.restype = c_int

            # Strategy functions
            self.SCOTCH_stratInit = self._get_func("SCOTCH_stratInit")
            self.SCOTCH_stratInit.argtypes = [POINTER(SCOTCH_Strat)]
            self.SCOTCH_stratInit.restype = c_int

            self.SCOTCH_stratExit = self._get_func("SCOTCH_stratExit")
            self.SCOTCH_stratExit.argtypes = [POINTER(SCOTCH_Strat)]
            self.SCOTCH_stratExit.restype = None

            self.SCOTCH_stratGraphMap = self._get_func("SCOTCH_stratGraphMap")
            self.SCOTCH_stratGraphMap.argtypes = [POINTER(SCOTCH_Strat), c_char_p]
            self.SCOTCH_stratGraphMap.restype = c_int

            self.SCOTCH_stratGraphOrder = self._get_func("SCOTCH_stratGraphOrder")
            self.SCOTCH_stratGraphOrder.argtypes = [POINTER(SCOTCH_Strat), c_char_p]
            self.SCOTCH_stratGraphOrder.restype = c_int

            # Architecture functions
            self.SCOTCH_archInit = self._get_func("SCOTCH_archInit")
            self.SCOTCH_archInit.argtypes = [POINTER(SCOTCH_Arch)]
            self.SCOTCH_archInit.restype = c_int

            self.SCOTCH_archExit = self._get_func("SCOTCH_archExit")
            self.SCOTCH_archExit.argtypes = [POINTER(SCOTCH_Arch)]
            self.SCOTCH_archExit.restype = None

            self.SCOTCH_archCmplt = self._get_func("SCOTCH_archCmplt")
            self.SCOTCH_archCmplt.argtypes = [POINTER(SCOTCH_Arch), self.SCOTCH_Num]
            self.SCOTCH_archCmplt.restype = c_int

            # Mapping functions
            self.SCOTCH_graphMapInit = self._get_func("SCOTCH_graphMapInit")
            self.SCOTCH_graphMapInit.argtypes = [
                POINTER(SCOTCH_Graph),
                POINTER(SCOTCH_Mapping),
                POINTER(SCOTCH_Arch),
                POINTER(self.SCOTCH_Num),
            ]
            self.SCOTCH_graphMapInit.restype = c_int

            self.SCOTCH_graphMapCompute = self._get_func("SCOTCH_graphMapCompute")
            self.SCOTCH_graphMapCompute.argtypes = [
                POINTER(SCOTCH_Graph),
                POINTER(SCOTCH_Mapping),
                POINTER(SCOTCH_Strat),
            ]
            self.SCOTCH_graphMapCompute.restype = c_int

            self.SCOTCH_graphMapExit = self._get_func("SCOTCH_graphMapExit")
            self.SCOTCH_graphMapExit.argtypes = [
                POINTER(SCOTCH_Graph),
                POINTER(SCOTCH_Mapping),
            ]
            self.SCOTCH_graphMapExit.restype = None

            # File I/O functions
            self.SCOTCH_graphLoad = self._get_func("SCOTCH_graphLoad")
            self.SCOTCH_graphLoad.argtypes = [
                POINTER(SCOTCH_Graph),
                c_void_p,  # FILE*
                self.SCOTCH_Num,  # baseval
                self.SCOTCH_Num,  # flag
            ]
            self.SCOTCH_graphLoad.restype = c_int

            self.SCOTCH_graphSave = self._get_func("SCOTCH_graphSave")
            self.SCOTCH_graphSave.argtypes = [
                POINTER(SCOTCH_Graph),
                c_void_p,  # FILE*
            ]
            self.SCOTCH_graphSave.restype = c_int

        except AttributeError as e:
            print(f"Warning: Some Scotch functions not found in variant: {e}", file=sys.stderr)

    def is_loaded(self) -> bool:
        """Check if this variant was successfully loaded."""
        return self._libscotch is not None

    def get_dtype(self):
        """Get the appropriate numpy dtype for this variant."""
        import numpy as np
        return np.int64 if self.int_size == 64 else np.int32

    def __repr__(self):
        return f"ScotchVariant({self.int_size}-bit, {'parallel' if self.parallel else 'sequential'})"


class ScotchVariantManager:
    """
    Manages multiple Scotch variants and provides switching capability.
    """

    def __init__(self):
        self.variants: Dict[Tuple[int, bool], ScotchVariant] = {}
        self._active: Optional[ScotchVariant] = None
        self._discover_and_load_variants()

    def _discover_and_load_variants(self):
        """Discover and load all available Scotch variants."""
        builds_dir = Path(__file__).parent.parent / "scotch-builds"

        if not builds_dir.exists():
            print(f"Warning: scotch-builds directory not found at {builds_dir}", file=sys.stderr)
            print("Run 'make build-all' to build Scotch variants", file=sys.stderr)
            return

        # Try to load all 4 possible variants
        for int_size in [32, 64]:
            for parallel in [False, True]:
                lib_dir = builds_dir / f"lib{int_size}"
                header_dir = builds_dir / f"inc{int_size}"

                if lib_dir.exists() and header_dir.exists():
                    try:
                        variant = ScotchVariant(int_size, parallel, lib_dir, header_dir)
                        if variant.is_loaded():
                            self.variants[(int_size, parallel)] = variant
                    except Exception as e:
                        print(f"Could not load variant ({int_size}-bit, "
                              f"{'parallel' if parallel else 'sequential'}): {e}",
                              file=sys.stderr)

        # Set default active variant (prefer environment, then 32-bit sequential)
        default_int_size = int(os.environ.get("PYSCOTCH_INT_SIZE", "32"))
        default_parallel = bool(int(os.environ.get("PYSCOTCH_PARALLEL", "0")))

        self.set_active(default_int_size, default_parallel)

    def set_active(self, int_size: int, parallel: bool = False) -> bool:
        """
        Set the active Scotch variant.

        Args:
            int_size: 32 or 64
            parallel: True for PT-Scotch, False for sequential

        Returns:
            True if variant was found and activated, False otherwise
        """
        key = (int_size, parallel)
        if key in self.variants:
            self._active = self.variants[key]
            print(f"→ Active variant: {self._active}", file=sys.stderr)
            return True
        else:
            print(f"Warning: Variant ({int_size}-bit, {'parallel' if parallel else 'sequential'}) not available",
                  file=sys.stderr)
            # Fall back to any available variant
            if self.variants and not self._active:
                self._active = next(iter(self.variants.values()))
                print(f"→ Using fallback variant: {self._active}", file=sys.stderr)
            return False

    def get_active(self) -> Optional[ScotchVariant]:
        """Get the currently active variant."""
        return self._active

    def list_available(self) -> list:
        """List all available variants."""
        return list(self.variants.keys())

    def has_variant(self, int_size: int, parallel: bool = False) -> bool:
        """Check if a specific variant is available."""
        return (int_size, parallel) in self.variants


# Global variant manager
_variant_manager = ScotchVariantManager()


def set_active_variant(int_size: int, parallel: bool = False) -> bool:
    """
    Switch to a different Scotch variant.

    Args:
        int_size: 32 or 64
        parallel: True for PT-Scotch, False for sequential

    Returns:
        True if successful, False if variant not available
    """
    return _variant_manager.set_active(int_size, parallel)


def get_active_variant() -> Optional[ScotchVariant]:
    """Get the currently active Scotch variant."""
    return _variant_manager.get_active()


def list_available_variants() -> list:
    """List all available Scotch variants as (int_size, parallel) tuples."""
    return _variant_manager.list_available()


def get_scotch_int_size() -> int:
    """Get the integer size of the active variant."""
    variant = get_active_variant()
    return variant.int_size if variant else 32


def get_scotch_dtype():
    """Get the numpy dtype for the active variant."""
    variant = get_active_variant()
    if variant:
        return variant.get_dtype()
    import numpy as np
    return np.int32


# Compatibility layer: expose active variant's attributes at module level
def __getattr__(name):
    """
    Provide backward compatibility by exposing active variant's attributes.

    This allows code like `libscotch.SCOTCH_graphInit(...)` to work.
    """
    variant = get_active_variant()
    if variant and hasattr(variant, name):
        return getattr(variant, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Export commonly used items
__all__ = [
    # Structures
    "SCOTCH_Graph",
    "SCOTCH_Mesh",
    "SCOTCH_Strat",
    "SCOTCH_Arch",
    "SCOTCH_Mapping",
    "SCOTCH_Ordering",
    "SCOTCH_Geom",
    # Variant management
    "ScotchVariant",
    "ScotchVariantManager",
    "set_active_variant",
    "get_active_variant",
    "list_available_variants",
    "get_scotch_int_size",
    "get_scotch_dtype",
]
