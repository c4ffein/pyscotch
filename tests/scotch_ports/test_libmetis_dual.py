"""
Ported from: external/scotch/src/check/test_libmetis_dual.c

METIS dual graph compatibility
"""

import pytest
import numpy as np
from pathlib import Path

from pyscotch import Graph
from pyscotch import libscotch as lib


@pytest.fixture(autouse=True, scope="module")
def ensure_variant():
    """Sequential Scotch only (not PT-Scotch)."""
    variant = lib.get_active_variant()
    if variant:
        lib.set_active_variant(variant.int_size, parallel=False)


class TestLibmetisDual:
    """Tests from test_libmetis_dual.c"""

    def test_placeholder(self):
        """Placeholder test - port actual tests from C file."""
        raise NotImplementedError("TODO: Port from test_libmetis_dual.c")
