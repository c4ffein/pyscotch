"""
Ported from: external/scotch/src/check/test_strat_par.c

Parallel strategies (PT-Scotch)
"""

import pytest
import numpy as np
from pathlib import Path

from pyscotch import Graph
from pyscotch import libscotch as lib


@pytest.fixture(autouse=True, scope="module")
def ensure_variant():
    """PT-Scotch parallel variant required."""
    variant = lib.get_active_variant()
    if variant:
        lib.set_active_variant(variant.int_size, parallel=True)


class TestStratPar:
    """Tests from test_strat_par.c"""

    def test_placeholder(self):
        """Placeholder test - port actual tests from C file."""
        raise NotImplementedError("TODO: Port from test_strat_par.c")
