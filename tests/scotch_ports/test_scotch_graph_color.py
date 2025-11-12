"""
Ported from: external/scotch/src/check/test_scotch_graph_color.c

Tests the SCOTCH_graphColor() routine for graph coloring.
"""

import pytest
import numpy as np
from pathlib import Path

from pyscotch import Graph
from pyscotch import libscotch as lib


@pytest.fixture(autouse=True, scope="module")
def ensure_sequential():
    """Sequential Scotch only (not PT-Scotch)."""
    variant = lib.get_active_variant()
    if variant and variant.parallel:
        lib.set_active_variant(variant.int_size, parallel=False)


class TestGraphColor:
    """Graph coloring tests from test_scotch_graph_color.c"""

    def test_color_triangle(self):
        """Color a simple triangle graph."""
        raise NotImplementedError("TODO: Port SCOTCH_graphColor")

    def test_color_grid(self):
        """Color a grid graph."""
        raise NotImplementedError("TODO: Port SCOTCH_graphColor")

    def test_color_verify(self):
        """Verify coloring is valid (no adjacent same color)."""
        raise NotImplementedError("TODO: Port SCOTCH_graphColor + verification")
