"""
Tests for dynamic opaque structure sizing.

This file verifies that:
1. Structure sizes are computed correctly from SCOTCH_*Sizeof() functions
2. Computed sizes match actual library requirements for the active variant
3. All structure types can be created and used without segfaults

These tests are critical because incorrect sizing leads to memory corruption
and segfaults that are difficult to debug.

Single-Variant Design:
Tests run with ONE Scotch variant, configured via environment variables:
- PYSCOTCH_INT_SIZE: 32 or 64 (default: 32)
- PYSCOTCH_PARALLEL: 0 or 1 (default: 0)
"""

import pytest
from ctypes import byref, sizeof
import numpy as np

from pyscotch import libscotch as lib


# TODO This file made sense with the multi-variant logic, should be adapted to the new constraints - hardcode more


class TestComputedSizesMatchSizeof:
    """Verify structure sizes match actual SCOTCH_*Sizeof() calls."""

    def test_graph_size_matches_sizeof(self):
        """Graph structure size matches SCOTCH_graphSizeof()."""
        expected = lib.SCOTCH_graphSizeof()
        actual = sizeof(lib.SCOTCH_Graph)
        assert actual >= expected, f"Graph struct too small: {actual} < {expected}"

    def test_strat_size_matches_sizeof(self):
        """Strategy structure size matches SCOTCH_stratSizeof()."""
        expected = lib.SCOTCH_stratSizeof()
        actual = sizeof(lib.SCOTCH_Strat)
        assert actual >= expected, f"Strat struct too small: {actual} < {expected}"

    def test_arch_size_matches_sizeof(self):
        """Architecture structure size matches SCOTCH_archSizeof()."""
        expected = lib.SCOTCH_archSizeof()
        actual = sizeof(lib.SCOTCH_Arch)
        assert actual >= expected, f"Arch struct too small: {actual} < {expected}"

    def test_mesh_size_matches_sizeof(self):
        """Mesh structure size matches SCOTCH_meshSizeof()."""
        expected = lib.SCOTCH_meshSizeof()
        actual = sizeof(lib.SCOTCH_Mesh)
        assert actual >= expected, f"Mesh struct too small: {actual} < {expected}"

    def test_geom_size_matches_sizeof(self):
        """Geometry structure size matches SCOTCH_geomSizeof()."""
        expected = lib.SCOTCH_geomSizeof()
        actual = sizeof(lib.SCOTCH_Geom)
        assert actual >= expected, f"Geom struct too small: {actual} < {expected}"

    def test_ordering_size_matches_sizeof(self):
        """Ordering structure size matches SCOTCH_orderSizeof()."""
        expected = lib.SCOTCH_orderSizeof()
        actual = sizeof(lib.SCOTCH_Ordering)
        assert actual >= expected, f"Ordering struct too small: {actual} < {expected}"

    def test_mapping_size_matches_sizeof(self):
        """Mapping structure size matches SCOTCH_mapSizeof()."""
        expected = lib.SCOTCH_mapSizeof()
        actual = sizeof(lib.SCOTCH_Mapping)
        assert actual >= expected, f"Mapping struct too small: {actual} < {expected}"

    @pytest.mark.parallel
    def test_dgraph_size_matches_sizeof(self):
        """Distributed graph size matches SCOTCH_dgraphSizeof() (parallel only)."""
        expected = lib.SCOTCH_dgraphSizeof()
        actual = sizeof(lib.SCOTCH_Dgraph)
        assert actual >= expected, f"Dgraph struct too small: {actual} < {expected}"


class TestAllStructureTypesHaveComputedSizes:
    """Ensure no structure type is forgotten in size computation."""

    # Sequential structures (always available)
    SEQUENTIAL_STRUCTURE_NAMES = ["Graph", "Mesh", "Strat", "Arch", "Mapping", "Ordering", "Geom"]
    # Parallel-only structures
    PARALLEL_STRUCTURE_NAMES = ["Dgraph"]

    def _get_structure_names(self):
        """Get structure names available for current variant."""
        names = list(self.SEQUENTIAL_STRUCTURE_NAMES)
        if lib.is_parallel():
            names.extend(self.PARALLEL_STRUCTURE_NAMES)
        return names

    def test_no_zero_sizes(self):
        """No structure has a zero computed size (would indicate failure)."""
        for struct_name in self._get_structure_names():
            struct_class = getattr(lib, f"SCOTCH_{struct_name}")
            if struct_class is None:
                continue  # Skip structures not available in current variant
            size = sizeof(struct_class)
            assert size > 0, f"Structure {struct_name} has zero size"

    def test_sizes_are_reasonable(self):
        """Sizes are within reasonable bounds (not absurdly large)."""
        MAX_REASONABLE_SIZE = 4096  # 4KB should be plenty for any Scotch structure
        for struct_name in self._get_structure_names():
            struct_class = getattr(lib, f"SCOTCH_{struct_name}")
            if struct_class is None:
                continue  # Skip structures not available in current variant
            size = sizeof(struct_class)
            assert size <= MAX_REASONABLE_SIZE, (
                f"Structure {struct_name} has suspicious size {size} bytes"
            )

    def test_strat_size_is_small(self):
        """Strategy is tiny - if it's large, dynamic sizing may have failed."""
        # Strategy is typically 8 bytes - if it's 512+, something is wrong
        size = sizeof(lib.SCOTCH_Strat)
        assert size < 100, (
            f"Strategy size {size} is suspiciously large - "
            "dynamic sizing may have failed"
        )


class TestStructureCreationAndBasicOperations:
    """Test each structure type can be created and used without segfaults."""

    def test_graph_create_init_exit(self):
        """Graph can be created, initialized, and cleaned up."""
        graph = lib.SCOTCH_Graph()
        ret = lib.SCOTCH_graphInit(byref(graph))
        assert ret == 0, "Graph init failed"
        lib.SCOTCH_graphExit(byref(graph))

    def test_graph_full_lifecycle(self):
        """Graph can be built and used for operations."""
        graph = lib.SCOTCH_Graph()
        ret = lib.SCOTCH_graphInit(byref(graph))
        assert ret == 0

        # Build a simple triangle graph
        dtype = lib.get_dtype()
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)

        from ctypes import POINTER
        ret = lib.SCOTCH_graphBuild(
            byref(graph),
            lib.SCOTCH_Num(0),  # baseval
            lib.SCOTCH_Num(3),  # vertnbr
            verttab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            None,  # vendtab
            None,  # velotab
            None,  # vlbltab
            lib.SCOTCH_Num(6),  # edgenbr
            edgetab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            None,  # edlotab
        )
        assert ret == 0, "Graph build failed"

        # Verify graph is valid
        ret = lib.SCOTCH_graphCheck(byref(graph))
        assert ret == 0, "Graph check failed"

        lib.SCOTCH_graphExit(byref(graph))

    def test_strat_create_init_exit(self):
        """Strategy can be created, initialized, and cleaned up."""
        strat = lib.SCOTCH_Strat()
        ret = lib.SCOTCH_stratInit(byref(strat))
        assert ret == 0, "Strategy init failed"
        lib.SCOTCH_stratExit(byref(strat))

    def test_strat_set_mapping(self):
        """Strategy can be configured for mapping."""
        strat = lib.SCOTCH_Strat()
        ret = lib.SCOTCH_stratInit(byref(strat))
        assert ret == 0

        # Set a mapping strategy
        from ctypes import c_char_p
        ret = lib.SCOTCH_stratGraphMap(byref(strat), c_char_p(b""))
        assert ret == 0, "Setting mapping strategy failed"

        lib.SCOTCH_stratExit(byref(strat))

    def test_arch_create_init_exit(self):
        """Architecture can be created, initialized, and cleaned up."""
        arch = lib.SCOTCH_Arch()
        ret = lib.SCOTCH_archInit(byref(arch))
        assert ret == 0, "Architecture init failed"
        lib.SCOTCH_archExit(byref(arch))

    def test_arch_complete(self):
        """Architecture can be configured as complete graph."""
        arch = lib.SCOTCH_Arch()
        ret = lib.SCOTCH_archInit(byref(arch))
        assert ret == 0

        # Set up as complete architecture with 4 processors
        ret = lib.SCOTCH_archCmplt(byref(arch), lib.SCOTCH_Num(4))
        assert ret == 0, "Architecture complete setup failed"

        lib.SCOTCH_archExit(byref(arch))

    def test_mesh_create_init_exit(self):
        """Mesh can be created, initialized, and cleaned up."""
        mesh = lib.SCOTCH_Mesh()
        ret = lib.SCOTCH_meshInit(byref(mesh))
        assert ret == 0, "Mesh init failed"
        lib.SCOTCH_meshExit(byref(mesh))

    def test_mapping_lifecycle(self):
        """Mapping can be created and used with a graph."""
        # Need a graph first
        graph = lib.SCOTCH_Graph()
        ret = lib.SCOTCH_graphInit(byref(graph))
        assert ret == 0

        # Build triangle graph
        dtype = lib.get_dtype()
        verttab = np.array([0, 2, 4, 6], dtype=dtype)
        edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=dtype)

        from ctypes import POINTER
        lib.SCOTCH_graphBuild(
            byref(graph),
            lib.SCOTCH_Num(0),
            lib.SCOTCH_Num(3),
            verttab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            None, None, None,
            lib.SCOTCH_Num(6),
            edgetab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
            None,
        )

        # Create architecture
        arch = lib.SCOTCH_Arch()
        lib.SCOTCH_archInit(byref(arch))
        lib.SCOTCH_archCmplt(byref(arch), lib.SCOTCH_Num(2))

        # Create mapping
        mapping = lib.SCOTCH_Mapping()
        parttab = np.zeros(3, dtype=dtype)

        ret = lib.SCOTCH_graphMapInit(
            byref(graph),
            byref(mapping),
            byref(arch),
            parttab.ctypes.data_as(POINTER(lib.SCOTCH_Num)),
        )
        assert ret == 0, "Mapping init failed"

        # Clean up in reverse order
        lib.SCOTCH_graphMapExit(byref(graph), byref(mapping))
        lib.SCOTCH_archExit(byref(arch))
        lib.SCOTCH_graphExit(byref(graph))


class TestDirectConstruction:
    """Test that direct structure construction works correctly."""

    def test_direct_construction_returns_correct_types(self):
        """Direct construction returns instances of the correct structure types."""
        assert isinstance(lib.SCOTCH_Graph(), getattr(lib, "SCOTCH_Graph"))
        assert isinstance(lib.SCOTCH_Strat(), getattr(lib, "SCOTCH_Strat"))
        assert isinstance(lib.SCOTCH_Arch(), getattr(lib, "SCOTCH_Arch"))
        assert isinstance(lib.SCOTCH_Mesh(), getattr(lib, "SCOTCH_Mesh"))
        assert isinstance(lib.SCOTCH_Geom(), getattr(lib, "SCOTCH_Geom"))
        assert isinstance(lib.SCOTCH_Ordering(), getattr(lib, "SCOTCH_Ordering"))
        assert isinstance(lib.SCOTCH_Mapping(), getattr(lib, "SCOTCH_Mapping"))

    @pytest.mark.parallel
    def test_dgraph_construction_returns_correct_type(self):
        """Dgraph construction returns correct type (parallel only)."""
        assert isinstance(lib.SCOTCH_Dgraph(), getattr(lib, "SCOTCH_Dgraph"))

    def test_multiple_structures_independent(self):
        """Multiple structures can be created and used independently."""
        # Create multiple graphs
        graphs = [lib.SCOTCH_Graph() for _ in range(5)]

        # Initialize all
        for g in graphs:
            ret = lib.SCOTCH_graphInit(byref(g))
            assert ret == 0

        # Clean up all
        for g in graphs:
            lib.SCOTCH_graphExit(byref(g))


class TestDgraphSizing:
    """Tests specific to distributed graph (PT-Scotch) sizing."""

    @pytest.mark.parallel
    def test_dgraph_size_is_positive(self):
        """Dgraph size is properly computed for parallel variants."""
        size = sizeof(lib.SCOTCH_Dgraph)
        assert size > 0, "Dgraph size should be positive"

    @pytest.mark.parallel
    def test_dgraph_larger_than_graph(self):
        """Dgraph structure is larger than regular graph (has MPI info)."""
        # Dgraph has additional fields for distributed processing
        dgraph_size = sizeof(lib.SCOTCH_Dgraph)
        graph_size = sizeof(lib.SCOTCH_Graph)
        assert dgraph_size > graph_size, (
            f"Dgraph ({dgraph_size}) should be larger than Graph ({graph_size})"
        )


class TestSizeDocumentation:
    """Tests that document expected sizes for reference."""

    def test_print_all_computed_sizes(self):
        """Document all computed sizes (useful for debugging)."""
        print("\n=== Computed Structure Sizes ===")
        # Sequential structures (always available)
        structure_names = ["Graph", "Strat", "Arch", "Mesh", "Geom", "Ordering", "Mapping"]
        for name in structure_names:
            struct_class = getattr(lib, f"SCOTCH_{name}")
            print(f"  {name.lower()}: {sizeof(struct_class)} bytes")
        # Dgraph only if parallel
        if lib.is_parallel():
            struct_class = getattr(lib, "SCOTCH_Dgraph")
            print(f"  dgraph: {sizeof(struct_class)} bytes")

    def test_print_sizeof_values(self):
        """Document SCOTCH_*Sizeof() return values."""
        print("\n=== SCOTCH_*Sizeof() Values ===")
        print(f"  graphSizeof: {lib.SCOTCH_graphSizeof()} bytes")
        print(f"  stratSizeof: {lib.SCOTCH_stratSizeof()} bytes")
        print(f"  archSizeof: {lib.SCOTCH_archSizeof()} bytes")
        print(f"  meshSizeof: {lib.SCOTCH_meshSizeof()} bytes")
        print(f"  geomSizeof: {lib.SCOTCH_geomSizeof()} bytes")
        print(f"  orderSizeof: {lib.SCOTCH_orderSizeof()} bytes")
        print(f"  mapSizeof: {lib.SCOTCH_mapSizeof()} bytes")
        print(f"  numSizeof: {lib.SCOTCH_numSizeof()} bytes")
