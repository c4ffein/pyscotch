"""
Architecture decomposition tests - FULLY PORTED

Tests architecture decomposition functionality including building, saving, and sub-architectures.
Corresponds to test_scotch_arch_deco.c from the Scotch test suite.
"""

import pytest
from pathlib import Path
import tempfile
import numpy as np
from ctypes import byref, POINTER, c_void_p

from pyscotch import Graph, Architecture, Strategy
from pyscotch import libscotch as lib
from pyscotch.graph import c_fopen


@pytest.mark.parametrize("int_size", [32, 64])
class TestScotchArchDeco:
    """Tests from test_scotch_arch_deco.c - decomposition architectures"""

    def test_arch_build_and_save(self, int_size):
        """Test building a decomposition-described architecture and saving it."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/m16x16_b1.grf")
        assert test_data.exists(), (
            f"Required test data missing: {test_data}. "
            f"Run 'git submodule update --init --recursive' to fetch Scotch test data."
        )

        # Load graph
        graph = Graph()
        graph.load(test_data)
        vertnbr, _ = graph.size()
        assert vertnbr >= 8, f"Graph too small: {vertnbr} < 8"

        # Create architecture and strategy
        arch = Architecture()
        strat = Strategy()

        # Build decomposition-described architecture with archBuild0
        # (uses automatic number of levels with a strategy)
        ret = lib.SCOTCH_archBuild0(
            byref(arch._arch),
            byref(graph._graph),
            lib.SCOTCH_Num(vertnbr),  # Use all vertices
            None,  # NULL listtab = use all vertices
            byref(strat._strat)
        )
        assert ret == 0, "SCOTCH_archBuild0 failed"

        # Save architecture to a file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.arch') as tmpfile:
            tmpfile_path = tmpfile.name

        try:
            with c_fopen(tmpfile_path, "w") as file_ptr:
                ret = lib.SCOTCH_archSave(byref(arch._arch), file_ptr)
                assert ret == 0, "SCOTCH_archSave failed"

            # Verify file was created and has content
            assert Path(tmpfile_path).exists()
            assert Path(tmpfile_path).stat().st_size > 0
        finally:
            Path(tmpfile_path).unlink(missing_ok=True)

    def test_arch_build2_without_strategy(self, int_size):
        """Test archBuild2 which doesn't require a strategy."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/m16x16_b1.grf")
        assert test_data.exists(), (
            f"Required test data missing: {test_data}. "
            f"Run 'git submodule update --init --recursive' to fetch Scotch test data."
        )

        # Load graph
        graph = Graph()
        graph.load(test_data)
        vertnbr, _ = graph.size()

        # Create architecture
        arch = Architecture()

        # Build with archBuild2 (no strategy needed)
        ret = lib.SCOTCH_archBuild2(
            byref(arch._arch),
            byref(graph._graph),
            lib.SCOTCH_Num(vertnbr),
            None  # NULL listtab = use all vertices
        )
        assert ret == 0, "SCOTCH_archBuild2 failed"

    def test_arch_sub(self, int_size):
        """Test creating a sub-architecture from an existing architecture."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/m16x16_b1.grf")
        assert test_data.exists(), (
            f"Required test data missing: {test_data}. "
            f"Run 'git submodule update --init --recursive' to fetch Scotch test data."
        )

        # Load graph and build architecture
        graph = Graph()
        graph.load(test_data)
        vertnbr, _ = graph.size()

        arch = Architecture()
        ret = lib.SCOTCH_archBuild2(
            byref(arch._arch),
            byref(graph._graph),
            lib.SCOTCH_Num(vertnbr),
            None
        )
        assert ret == 0, "archBuild2 failed"

        # Create a list of domains to extract
        listnbr = min(5, vertnbr)  # Use first 5 vertices (or fewer if graph is small)
        listtab = np.arange(listnbr, dtype=lib.get_dtype())

        # Create sub-architecture
        sub_arch = Architecture()
        ret = lib.SCOTCH_archSub(
            byref(sub_arch._arch),
            byref(arch._arch),
            lib.SCOTCH_Num(listnbr),
            listtab.ctypes.data_as(POINTER(lib.SCOTCH_Num))
        )
        assert ret == 0, "SCOTCH_archSub failed"

    def test_arch_load(self, int_size):
        """Test saving and loading an architecture."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        test_data = Path("external/scotch/src/check/data/m16x16_b1.grf")
        assert test_data.exists(), (
            f"Required test data missing: {test_data}. "
            f"Run 'git submodule update --init --recursive' to fetch Scotch test data."
        )

        # Build an architecture
        graph = Graph()
        graph.load(test_data)
        vertnbr, _ = graph.size()

        arch1 = Architecture()
        ret = lib.SCOTCH_archBuild2(
            byref(arch1._arch),
            byref(graph._graph),
            lib.SCOTCH_Num(vertnbr),
            None
        )
        assert ret == 0, "archBuild2 failed"

        # Save to file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.arch') as tmpfile:
            tmpfile_path = tmpfile.name

        try:
            # Save
            with c_fopen(tmpfile_path, "w") as file_ptr:
                ret = lib.SCOTCH_archSave(byref(arch1._arch), file_ptr)
                assert ret == 0, "archSave failed"

            # Load into a new architecture
            arch2 = Architecture()
            with c_fopen(tmpfile_path, "r") as file_ptr:
                ret = lib.SCOTCH_archLoad(byref(arch2._arch), file_ptr)
                assert ret == 0, "archLoad failed"

        finally:
            Path(tmpfile_path).unlink(missing_ok=True)

    def test_basic_architecture_creation(self, int_size):
        """Test basic architecture creation (complete graph architecture)."""
        # Set variant for this test
        lib.set_active_variant(int_size, parallel=False)
        arch = Architecture.complete_graph(5)
        # Architecture created successfully
