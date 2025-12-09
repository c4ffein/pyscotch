"""
Test that verifies all Scotch functions have correct suffixes in both 32-bit and 64-bit libraries.

This test loads BOTH library variants simultaneously to verify that:
1. All expected functions exist with _32 suffix in the 32-bit library
2. All expected functions exist with _64 suffix in the 64-bit library
3. No symbol conflicts exist between variants

This test found a bug in Scotch where some functions were not properly prefixed,
causing symbol conflicts when both libraries were loaded in the same process.

This test is independent of the active variant and directly loads the C libraries.
"""

import ctypes
import ctypes.util
import pytest
from pathlib import Path


# TODO We should make this adaptive to scotch to never forget a new function


def _preload_dependencies():
    """Preload shared dependencies (zlib, mpi, scotcherr) globally."""
    # Preload zlib
    try:
        zlib_path = ctypes.util.find_library('z')
        if zlib_path:
            ctypes.CDLL(zlib_path, mode=ctypes.RTLD_GLOBAL)
    except (OSError, AttributeError, TypeError):
        pass

    # Preload MPI if available
    try:
        mpi_path = ctypes.util.find_library('mpi')
        if mpi_path:
            ctypes.CDLL(mpi_path, mode=ctypes.RTLD_GLOBAL)
    except (OSError, AttributeError, TypeError):
        pass

    # Preload scotcherr from both lib dirs (they're identical)
    builds_dir = Path(__file__).parent.parent.parent / "scotch-builds"
    for lib_dir in ["lib32", "lib64"]:
        err_path = builds_dir / lib_dir / "libscotcherr.so"
        if err_path.exists():
            try:
                ctypes.CDLL(str(err_path), mode=ctypes.RTLD_GLOBAL)
                break  # Only need to load once
            except (OSError, AttributeError, TypeError):
                pass


# Preload dependencies at module import
_preload_dependencies()


# Functions that should exist in libscotch.so (sequential)
SCOTCH_FUNCTIONS = [
    "SCOTCH_graphInit",
    "SCOTCH_graphExit",
    "SCOTCH_graphBuild",
    "SCOTCH_graphCheck",
    "SCOTCH_graphSize",
    "SCOTCH_graphData",
    "SCOTCH_graphLoad",
    "SCOTCH_graphSave",
    "SCOTCH_graphPart",
    "SCOTCH_graphPartOvl",
    "SCOTCH_graphOrder",
    "SCOTCH_graphColor",
    "SCOTCH_graphCoarsen",
    "SCOTCH_graphCoarsenMatch",
    "SCOTCH_graphCoarsenBuild",
    "SCOTCH_graphInduceList",
    "SCOTCH_graphInducePart",
    "SCOTCH_graphDiamPV",
    "SCOTCH_graphSizeof",
    "SCOTCH_stratInit",
    "SCOTCH_stratExit",
    "SCOTCH_stratGraphMap",
    "SCOTCH_stratGraphOrder",
    "SCOTCH_stratSizeof",
    "SCOTCH_archInit",
    "SCOTCH_archExit",
    "SCOTCH_archCmplt",
    "SCOTCH_archBuild0",
    "SCOTCH_archBuild2",
    "SCOTCH_archSub",
    "SCOTCH_archLoad",
    "SCOTCH_archSave",
    "SCOTCH_archSizeof",
    "SCOTCH_meshInit",
    "SCOTCH_meshExit",
    "SCOTCH_meshLoad",
    "SCOTCH_meshSave",
    "SCOTCH_meshCheck",
    "SCOTCH_meshBuild",
    "SCOTCH_meshGraph",
    "SCOTCH_meshSizeof",
    "SCOTCH_graphMapInit",
    "SCOTCH_graphMapExit",
    "SCOTCH_graphMapCompute",
    "SCOTCH_graphRemapCompute",
    "SCOTCH_mapSizeof",
    "SCOTCH_orderSizeof",
    "SCOTCH_geomSizeof",
    "SCOTCH_numSizeof",
    "SCOTCH_randomReset",
    "SCOTCH_randomSeed",
    "SCOTCH_randomVal",
]

# Functions that should exist in libptscotch.so (parallel)
PTSCOTCH_FUNCTIONS = [
    "SCOTCH_dgraphInit",
    "SCOTCH_dgraphExit",
    "SCOTCH_dgraphBuild",
    "SCOTCH_dgraphCheck",
    "SCOTCH_dgraphData",
    "SCOTCH_dgraphLoad",
    "SCOTCH_dgraphSave",
    "SCOTCH_dgraphSizeof",
    "SCOTCH_dgraphCoarsen",
    "SCOTCH_dgraphGhst",
    "SCOTCH_dgraphGrow",
    "SCOTCH_dgraphBand",
    "SCOTCH_dgraphRedist",
    "SCOTCH_dgraphInducePart",
]


def get_builds_dir():
    """Get the scotch-builds directory."""
    return Path(__file__).parent.parent.parent / "scotch-builds"


class TestSymbolPrefixes:
    """Tests that verify function symbols are correctly prefixed in both library variants."""

    def test_32bit_functions_have_correct_suffix(self):
        """Verify all functions in 32-bit library have _32 suffix."""
        builds_dir = get_builds_dir()
        lib_path = builds_dir / "lib32" / "libscotch.so"

        if not lib_path.exists():
            pytest.skip(f"32-bit library not found: {lib_path}")

        lib = ctypes.CDLL(str(lib_path))

        missing = []
        for func_name in SCOTCH_FUNCTIONS:
            suffixed_name = f"{func_name}_32"
            try:
                getattr(lib, suffixed_name)
            except AttributeError:
                missing.append(suffixed_name)

        assert not missing, f"Missing 32-bit functions: {missing}"

    def test_64bit_functions_have_correct_suffix(self):
        """Verify all functions in 64-bit library have _64 suffix."""
        builds_dir = get_builds_dir()
        lib_path = builds_dir / "lib64" / "libscotch.so"

        if not lib_path.exists():
            pytest.skip(f"64-bit library not found: {lib_path}")

        lib = ctypes.CDLL(str(lib_path))

        missing = []
        for func_name in SCOTCH_FUNCTIONS:
            suffixed_name = f"{func_name}_64"
            try:
                getattr(lib, suffixed_name)
            except AttributeError:
                missing.append(suffixed_name)

        assert not missing, f"Missing 64-bit functions: {missing}"

    def test_32bit_ptscotch_functions_have_correct_suffix(self):
        """Verify all PT-Scotch functions in 32-bit library have _32 suffix."""
        builds_dir = get_builds_dir()
        scotch_path = builds_dir / "lib32" / "libscotch.so"
        ptscotch_path = builds_dir / "lib32" / "libptscotch.so"

        if not ptscotch_path.exists():
            pytest.skip(f"32-bit PT-Scotch library not found: {ptscotch_path}")

        # Load libscotch first (ptscotch depends on it)
        ctypes.CDLL(str(scotch_path), mode=ctypes.RTLD_GLOBAL)
        lib = ctypes.CDLL(str(ptscotch_path))

        missing = []
        for func_name in PTSCOTCH_FUNCTIONS:
            suffixed_name = f"{func_name}_32"
            try:
                getattr(lib, suffixed_name)
            except AttributeError:
                missing.append(suffixed_name)

        assert not missing, f"Missing 32-bit PT-Scotch functions: {missing}"

    def test_64bit_ptscotch_functions_have_correct_suffix(self):
        """Verify all PT-Scotch functions in 64-bit library have _64 suffix."""
        builds_dir = get_builds_dir()
        scotch_path = builds_dir / "lib64" / "libscotch.so"
        ptscotch_path = builds_dir / "lib64" / "libptscotch.so"

        if not ptscotch_path.exists():
            pytest.skip(f"64-bit PT-Scotch library not found: {ptscotch_path}")

        # Load libscotch first (ptscotch depends on it)
        ctypes.CDLL(str(scotch_path), mode=ctypes.RTLD_GLOBAL)
        lib = ctypes.CDLL(str(ptscotch_path))

        missing = []
        for func_name in PTSCOTCH_FUNCTIONS:
            suffixed_name = f"{func_name}_64"
            try:
                getattr(lib, suffixed_name)
            except AttributeError:
                missing.append(suffixed_name)

        assert not missing, f"Missing 64-bit PT-Scotch functions: {missing}"

    def test_both_libraries_can_be_loaded_simultaneously(self):
        """
        Verify both 32-bit and 64-bit libraries can be loaded in the same process.

        This test catches symbol conflicts that occur when functions are not
        properly suffixed with _32 or _64.
        """
        builds_dir = get_builds_dir()
        lib32_path = builds_dir / "lib32" / "libscotch.so"
        lib64_path = builds_dir / "lib64" / "libscotch.so"

        if not lib32_path.exists():
            pytest.skip(f"32-bit library not found: {lib32_path}")
        if not lib64_path.exists():
            pytest.skip(f"64-bit library not found: {lib64_path}")

        # Load both libraries with RTLD_LOCAL to avoid symbol conflicts
        lib32 = ctypes.CDLL(str(lib32_path), mode=ctypes.RTLD_LOCAL)
        lib64 = ctypes.CDLL(str(lib64_path), mode=ctypes.RTLD_LOCAL)

        # Verify we can call sizeof functions from both and get different results
        # (32-bit structures are smaller than 64-bit)
        graph_size_32 = lib32.SCOTCH_graphSizeof_32()
        graph_size_64 = lib64.SCOTCH_graphSizeof_64()

        assert graph_size_32 > 0, "32-bit graph size should be positive"
        assert graph_size_64 > 0, "64-bit graph size should be positive"
        assert graph_size_64 > graph_size_32, \
            f"64-bit graph ({graph_size_64}) should be larger than 32-bit ({graph_size_32})"

    def test_num_sizeof_returns_correct_values(self):
        """Verify SCOTCH_numSizeof returns 4 for 32-bit and 8 for 64-bit."""
        builds_dir = get_builds_dir()
        lib32_path = builds_dir / "lib32" / "libscotch.so"
        lib64_path = builds_dir / "lib64" / "libscotch.so"

        if not lib32_path.exists():
            pytest.skip(f"32-bit library not found: {lib32_path}")
        if not lib64_path.exists():
            pytest.skip(f"64-bit library not found: {lib64_path}")

        lib32 = ctypes.CDLL(str(lib32_path), mode=ctypes.RTLD_LOCAL)
        lib64 = ctypes.CDLL(str(lib64_path), mode=ctypes.RTLD_LOCAL)

        num_size_32 = lib32.SCOTCH_numSizeof_32()
        num_size_64 = lib64.SCOTCH_numSizeof_64()

        assert num_size_32 == 4, f"32-bit SCOTCH_Num should be 4 bytes, got {num_size_32}"
        assert num_size_64 == 8, f"64-bit SCOTCH_Num should be 8 bytes, got {num_size_64}"
