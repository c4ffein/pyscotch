"""
Ported from: external/scotch/src/check/test_multilib.c

Multi-library support test - NOW WORKING with compat layer!

Tests that multiple Scotch library variants (32-bit and 64-bit) can coexist
in the same process, loading graphs and performing operations with each.

Previously blocked by FILE* API, now works thanks to libpyscotch_compat.so
"""

import pytest
from pathlib import Path

from pyscotch import Graph
from pyscotch import libscotch as lib


class TestMultilib:
    """Tests from test_multilib.c - multi-variant coexistence"""

    def test_multilib_32_and_64_bit(self):
        """Test loading same graph with both 32-bit and 64-bit Scotch variants.

        This verifies that PyScotch can switch between variants correctly and
        that both can load the same graph file.
        """
        test_data = Path("external/scotch/src/check/data/m4x4_b1.grf")

        if not test_data.exists():
            pytest.skip(f"Test data file not found: {test_data}")

        # Try to set 32-bit variant
        if not lib.set_active_variant(32, parallel=False):
            pytest.skip("32-bit Scotch variant not available")

        # Load with 32-bit variant
        graph_32 = Graph()
        graph_32.load(test_data)

        # Verify 32-bit graph
        assert graph_32.check(), "32-bit graph failed check"
        v32, e32 = graph_32.size()
        assert v32 > 0, "32-bit graph has no vertices"

        # Cleanup 32-bit graph BEFORE switching variants
        # (must destroy with same variant that created it)
        del graph_32

        # Try to set 64-bit variant
        if not lib.set_active_variant(64, parallel=False):
            pytest.skip("64-bit Scotch variant not available")

        # Load with 64-bit variant
        graph_64 = Graph()
        graph_64.load(test_data)

        # Verify 64-bit graph
        assert graph_64.check(), "64-bit graph failed check"
        v64, e64 = graph_64.size()
        assert v64 > 0, "64-bit graph has no vertices"

        # Both should have same graph structure
        assert v32 == v64, f"Vertex count mismatch: 32-bit={v32}, 64-bit={v64}"
        assert e32 == e64, f"Edge count mismatch: 32-bit={e32}, 64-bit={e64}"

        # Cleanup 64-bit graph
        del graph_64

    def test_variant_switching(self):
        """Test switching between variants multiple times."""
        # Create small programmatic graphs with each variant
        edges = [(0, 1), (1, 2), (2, 0)]

        # 32-bit
        lib.set_active_variant(32, parallel=False)
        g32_1 = Graph.from_edges(edges, num_vertices=3)
        v1, e1 = g32_1.size()
        # Cleanup before switching variants
        del g32_1

        # Switch to 64-bit
        lib.set_active_variant(64, parallel=False)
        g64 = Graph.from_edges(edges, num_vertices=3)
        v2, e2 = g64.size()
        # Cleanup before switching variants
        del g64

        # Switch back to 32-bit
        lib.set_active_variant(32, parallel=False)
        g32_2 = Graph.from_edges(edges, num_vertices=3)
        v3, e3 = g32_2.size()
        # Cleanup
        del g32_2

        # All should have same size
        assert v1 == v2 == v3 == 3
        assert e1 == e2 == e3 == 6
