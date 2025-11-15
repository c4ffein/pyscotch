"""
Ported from: external/scotch/src/check/test_common_random.c

Common random number generation tests.

IMPORTANT: The C test uses INTERNAL API functions (intRandInit, intRandVal, etc.)
that take an explicit IntRandContext* argument. These are NOT part of the public
API in scotch.h and are not exposed to external library users.

The public API equivalent functions are:
- SCOTCH_randomReset() instead of intRandReset(&context)
- SCOTCH_randomVal(n) instead of intRandVal(&context, n)
- SCOTCH_randomSeed(n) instead of intRandSeed(&context, n)

The key difference is that the internal API allows multiple independent RNG contexts,
while the public API uses a single global context.

We port only the parts of this test that use public API. The internal API tests
are not relevant for PyScotch which only exposes the public scotch.h interface.

Additional tests using the public API are in:
- tests/pyscotch_base/test_random_enhanced.py (comprehensive public API tests)
"""

import pytest
from pyscotch import libscotch as lib


@pytest.fixture(autouse=True, scope="module")
def ensure_variant():
    """Sequential Scotch only (not PT-Scotch)."""
    variant = lib.get_active_variant()
    if variant:
        lib.set_active_variant(variant.int_size, parallel=False)


class TestCommonRandom:
    """Tests from test_common_random.c

    The C test performs two passes:
    1. First pass: generate values, reset, verify determinism, save state
    2. Second pass: load values, verify time-based seeding differs, load state

    We port the core functionality, skipping FILE* save/load operations.
    """

    def test_random_reset_determinism(self):
        """Test that SCOTCH_randomReset() makes sequences deterministic.

        Matches C test lines 95-115, but uses public API:
        - C test uses: intRandInit(&intranddat), intRandVal(&intranddat, max)
        - We use: SCOTCH_randomReset(), SCOTCH_randomVal(max)

        The behavior is equivalent - both test deterministic sequence generation.
        """
        RANDNBR = 100
        INTVALMAX = 10000

        # Initialize and generate first sequence (like intRandInit + intRandVal loop)
        lib.SCOTCH_randomReset()
        randtab = [lib.SCOTCH_randomVal(INTVALMAX) for _ in range(RANDNBR)]

        # Reset (line 100: intRandReset)
        lib.SCOTCH_randomReset()

        # Generate second sequence and verify it matches (lines 111-115)
        for randnum in range(RANDNBR):
            val = lib.SCOTCH_randomVal(INTVALMAX)
            assert randtab[randnum] == val, \
                f"After reset, value {randnum} differs: {randtab[randnum]} != {val}"

    # Note: The C test's "two consecutive runs yield different values" test
    # (lines 155-170) checks time-based seeding across separate process runs.
    # This is difficult to test in pytest without subprocess spawning.
    # The test also depends on compile-time flags (COMMON_DEBUG, COMMON_RANDOM_FIXED_SEED).

    @pytest.mark.skip(reason="FILE* operations cause segfaults - see QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4")
    def test_random_save_load_state(self):
        """Test random state save/load (lines 122-206 in C test).

        The C test uses intRandSave() and intRandLoad() with FILE* pointers
        to save/restore RNG state. We skip this due to Python ctypes FILE* issues.
        """
        pass
