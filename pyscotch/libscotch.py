"""
Low-level ctypes bindings to the PT-Scotch C library.
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

# Constants
# Size in bytes for opaque C structure placeholders
# This must be large enough to hold the actual Scotch C structures
_OPAQUE_STRUCTURE_SIZE = 256

# Type definitions matching Scotch's types
SCOTCH_Num = c_long
SCOTCH_Idx = c_long

# Find and load the Scotch library
def _find_library():
    """Locate the Scotch shared library."""
    # Check in the lib directory first
    lib_dir = Path(__file__).parent.parent / "lib"

    if sys.platform == "darwin":
        lib_names = ["libscotch.dylib", "libscotch.so"]
    elif sys.platform == "win32":
        lib_names = ["scotch.dll", "libscotch.dll"]
    else:
        lib_names = ["libscotch.so", "libscotch.so.0"]

    # Try local lib directory first
    for lib_name in lib_names:
        lib_path = lib_dir / lib_name
        if lib_path.exists():
            return str(lib_path)

    # Try system paths
    for lib_name in lib_names:
        try:
            return ctypes.util.find_library(lib_name.replace("lib", "").replace(".so", "").replace(".dylib", ""))
        except (OSError, AttributeError, TypeError):
            # OSError: Library loading failed
            # AttributeError: ctypes.util not available
            # TypeError: Invalid library name
            continue

    return None

# Load library
_lib_path = _find_library()
if _lib_path:
    try:
        # Preload dependencies first (zlib is required by libscotch)
        try:
            zlib_path = ctypes.util.find_library('z')
            if zlib_path:
                ctypes.CDLL(zlib_path, mode=ctypes.RTLD_GLOBAL)
        except (OSError, AttributeError, TypeError):
            # zlib preload failed, but continue
            pass

        # Load error library (required by libscotch)
        lib_dir = Path(_lib_path).parent
        if sys.platform == "darwin":
            err_lib_names = ["libscotcherr.dylib"]
        elif sys.platform == "win32":
            err_lib_names = ["scotcherr.dll", "libscotcherr.dll"]
        else:
            err_lib_names = ["libscotcherr.so"]

        for err_lib_name in err_lib_names:
            err_lib_path = lib_dir / err_lib_name
            if err_lib_path.exists():
                try:
                    ctypes.CDLL(str(err_lib_path), mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    # Error library load failed, but continue trying main library
                    pass
                break

        _libscotch = ctypes.CDLL(_lib_path, mode=ctypes.RTLD_GLOBAL)
    except OSError as e:
        _libscotch = None
        print(f"Warning: Could not load Scotch library from {_lib_path}: {e}", file=sys.stderr)
else:
    _libscotch = None
    print("Warning: Scotch library not found. Build it with 'make build-scotch'", file=sys.stderr)


# Opaque structure types (as used in Scotch)
# These structures need to be large enough to hold the actual C structures
# We use byte arrays to reserve the space without knowing the exact layout

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


# Function signatures
if _libscotch:
    # Graph functions
    try:
        # SCOTCH_graphInit
        SCOTCH_graphInit = _libscotch.SCOTCH_graphInit
        SCOTCH_graphInit.argtypes = [POINTER(SCOTCH_Graph)]
        SCOTCH_graphInit.restype = c_int

        # SCOTCH_graphExit
        SCOTCH_graphExit = _libscotch.SCOTCH_graphExit
        SCOTCH_graphExit.argtypes = [POINTER(SCOTCH_Graph)]
        SCOTCH_graphExit.restype = None

        # SCOTCH_graphLoad
        SCOTCH_graphLoad = _libscotch.SCOTCH_graphLoad
        SCOTCH_graphLoad.argtypes = [POINTER(SCOTCH_Graph), c_void_p, SCOTCH_Num, SCOTCH_Num]
        SCOTCH_graphLoad.restype = c_int

        # SCOTCH_graphSave
        SCOTCH_graphSave = _libscotch.SCOTCH_graphSave
        SCOTCH_graphSave.argtypes = [POINTER(SCOTCH_Graph), c_void_p]
        SCOTCH_graphSave.restype = c_int

        # SCOTCH_graphBuild
        SCOTCH_graphBuild = _libscotch.SCOTCH_graphBuild
        SCOTCH_graphBuild.argtypes = [
            POINTER(SCOTCH_Graph),
            SCOTCH_Num,  # baseval
            SCOTCH_Num,  # vertnbr
            POINTER(SCOTCH_Num),  # verttab
            POINTER(SCOTCH_Num),  # vendtab
            POINTER(SCOTCH_Num),  # velotab
            POINTER(SCOTCH_Num),  # vlbltab
            SCOTCH_Num,  # edgenbr
            POINTER(SCOTCH_Num),  # edgetab
            POINTER(SCOTCH_Num),  # edlotab
        ]
        SCOTCH_graphBuild.restype = c_int

        # SCOTCH_graphCheck
        SCOTCH_graphCheck = _libscotch.SCOTCH_graphCheck
        SCOTCH_graphCheck.argtypes = [POINTER(SCOTCH_Graph)]
        SCOTCH_graphCheck.restype = c_int

        # SCOTCH_graphSize
        SCOTCH_graphSize = _libscotch.SCOTCH_graphSize
        SCOTCH_graphSize.argtypes = [
            POINTER(SCOTCH_Graph),
            POINTER(SCOTCH_Num),  # vertnbr
            POINTER(SCOTCH_Num),  # edgenbr
        ]
        SCOTCH_graphSize.restype = None

        # SCOTCH_graphData
        SCOTCH_graphData = _libscotch.SCOTCH_graphData
        SCOTCH_graphData.argtypes = [
            POINTER(SCOTCH_Graph),
            POINTER(SCOTCH_Num),  # baseval
            POINTER(SCOTCH_Num),  # vertnbr
            POINTER(POINTER(SCOTCH_Num)),  # verttab
            POINTER(POINTER(SCOTCH_Num)),  # vendtab
            POINTER(POINTER(SCOTCH_Num)),  # velotab
            POINTER(POINTER(SCOTCH_Num)),  # vlbltab
            POINTER(SCOTCH_Num),  # edgenbr
            POINTER(POINTER(SCOTCH_Num)),  # edgetab
            POINTER(POINTER(SCOTCH_Num)),  # edlotab
        ]
        SCOTCH_graphData.restype = None

        # SCOTCH_graphPart
        SCOTCH_graphPart = _libscotch.SCOTCH_graphPart
        SCOTCH_graphPart.argtypes = [
            POINTER(SCOTCH_Graph),
            SCOTCH_Num,  # partnbr
            POINTER(SCOTCH_Strat),
            POINTER(SCOTCH_Num),  # parttab
        ]
        SCOTCH_graphPart.restype = c_int

        # SCOTCH_graphMap
        SCOTCH_graphMap = _libscotch.SCOTCH_graphMap
        SCOTCH_graphMap.argtypes = [
            POINTER(SCOTCH_Graph),
            POINTER(SCOTCH_Arch),
            POINTER(SCOTCH_Strat),
            POINTER(SCOTCH_Num),  # maptab
        ]
        SCOTCH_graphMap.restype = c_int

        # SCOTCH_graphMapInit
        SCOTCH_graphMapInit = _libscotch.SCOTCH_graphMapInit
        SCOTCH_graphMapInit.argtypes = [
            POINTER(SCOTCH_Graph),
            POINTER(SCOTCH_Mapping),
            POINTER(SCOTCH_Arch),
            POINTER(SCOTCH_Num),  # parttab
        ]
        SCOTCH_graphMapInit.restype = c_int

        # SCOTCH_graphMapCompute
        SCOTCH_graphMapCompute = _libscotch.SCOTCH_graphMapCompute
        SCOTCH_graphMapCompute.argtypes = [
            POINTER(SCOTCH_Graph),
            POINTER(SCOTCH_Mapping),
            POINTER(SCOTCH_Strat),
        ]
        SCOTCH_graphMapCompute.restype = c_int

        # SCOTCH_graphMapExit
        SCOTCH_graphMapExit = _libscotch.SCOTCH_graphMapExit
        SCOTCH_graphMapExit.argtypes = [
            POINTER(SCOTCH_Graph),
            POINTER(SCOTCH_Mapping),
        ]
        SCOTCH_graphMapExit.restype = None

        # SCOTCH_graphOrder
        SCOTCH_graphOrder = _libscotch.SCOTCH_graphOrder
        SCOTCH_graphOrder.argtypes = [
            POINTER(SCOTCH_Graph),
            POINTER(SCOTCH_Strat),
            POINTER(SCOTCH_Num),  # permtab
            POINTER(SCOTCH_Num),  # peritab
            POINTER(SCOTCH_Num),  # cblkptr
            POINTER(SCOTCH_Num),  # rangtab
            POINTER(SCOTCH_Num),  # treetab
        ]
        SCOTCH_graphOrder.restype = c_int

        # Strategy functions
        SCOTCH_stratInit = _libscotch.SCOTCH_stratInit
        SCOTCH_stratInit.argtypes = [POINTER(SCOTCH_Strat)]
        SCOTCH_stratInit.restype = c_int

        SCOTCH_stratExit = _libscotch.SCOTCH_stratExit
        SCOTCH_stratExit.argtypes = [POINTER(SCOTCH_Strat)]
        SCOTCH_stratExit.restype = None

        SCOTCH_stratGraphMap = _libscotch.SCOTCH_stratGraphMap
        SCOTCH_stratGraphMap.argtypes = [POINTER(SCOTCH_Strat), c_char_p]
        SCOTCH_stratGraphMap.restype = c_int

        SCOTCH_stratGraphOrder = _libscotch.SCOTCH_stratGraphOrder
        SCOTCH_stratGraphOrder.argtypes = [POINTER(SCOTCH_Strat), c_char_p]
        SCOTCH_stratGraphOrder.restype = c_int

        SCOTCH_stratGraphClusterBuild = _libscotch.SCOTCH_stratGraphClusterBuild
        SCOTCH_stratGraphClusterBuild.argtypes = [POINTER(SCOTCH_Strat), c_char_p]
        SCOTCH_stratGraphClusterBuild.restype = c_int

        # Architecture functions
        SCOTCH_archInit = _libscotch.SCOTCH_archInit
        SCOTCH_archInit.argtypes = [POINTER(SCOTCH_Arch)]
        SCOTCH_archInit.restype = c_int

        SCOTCH_archExit = _libscotch.SCOTCH_archExit
        SCOTCH_archExit.argtypes = [POINTER(SCOTCH_Arch)]
        SCOTCH_archExit.restype = None

        SCOTCH_archCmplt = _libscotch.SCOTCH_archCmplt
        SCOTCH_archCmplt.argtypes = [POINTER(SCOTCH_Arch), SCOTCH_Num]
        SCOTCH_archCmplt.restype = c_int

        # Mesh functions
        SCOTCH_meshInit = _libscotch.SCOTCH_meshInit
        SCOTCH_meshInit.argtypes = [POINTER(SCOTCH_Mesh)]
        SCOTCH_meshInit.restype = c_int

        SCOTCH_meshExit = _libscotch.SCOTCH_meshExit
        SCOTCH_meshExit.argtypes = [POINTER(SCOTCH_Mesh)]
        SCOTCH_meshExit.restype = None

        SCOTCH_meshLoad = _libscotch.SCOTCH_meshLoad
        SCOTCH_meshLoad.argtypes = [POINTER(SCOTCH_Mesh), c_void_p, SCOTCH_Num]
        SCOTCH_meshLoad.restype = c_int

        SCOTCH_meshSave = _libscotch.SCOTCH_meshSave
        SCOTCH_meshSave.argtypes = [POINTER(SCOTCH_Mesh), c_void_p]
        SCOTCH_meshSave.restype = c_int

        SCOTCH_meshBuild = _libscotch.SCOTCH_meshBuild
        SCOTCH_meshBuild.argtypes = [
            POINTER(SCOTCH_Mesh),
            SCOTCH_Num,  # velmbas
            SCOTCH_Num,  # vnodbas
            SCOTCH_Num,  # velmnbr
            SCOTCH_Num,  # vnodnbr
            POINTER(SCOTCH_Num),  # verttab
            POINTER(SCOTCH_Num),  # vendtab
            POINTER(SCOTCH_Num),  # velotab
            POINTER(SCOTCH_Num),  # vnlotab
            POINTER(SCOTCH_Num),  # vlbltab
            SCOTCH_Num,  # edgenbr
            POINTER(SCOTCH_Num),  # edgetab
        ]
        SCOTCH_meshBuild.restype = c_int

        SCOTCH_meshCheck = _libscotch.SCOTCH_meshCheck
        SCOTCH_meshCheck.argtypes = [POINTER(SCOTCH_Mesh)]
        SCOTCH_meshCheck.restype = c_int

        SCOTCH_meshGraph = _libscotch.SCOTCH_meshGraph
        SCOTCH_meshGraph.argtypes = [POINTER(SCOTCH_Mesh), POINTER(SCOTCH_Graph)]
        SCOTCH_meshGraph.restype = c_int

    except AttributeError as e:
        print(f"Warning: Some Scotch functions not found: {e}", file=sys.stderr)


__all__ = [
    "SCOTCH_Graph",
    "SCOTCH_Mesh",
    "SCOTCH_Strat",
    "SCOTCH_Arch",
    "SCOTCH_Mapping",
    "SCOTCH_Ordering",
    "SCOTCH_Geom",
    "SCOTCH_Num",
    "SCOTCH_Idx",
]
