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



class TestCommonRandom:
    """Tests from test_common_random.c

    The C test performs two passes:
    1. First pass: generate values, reset, verify determinism, save state
    2. Second pass: load values, verify time-based seeding differs, load state
    """

    def test_random_reset_determinism(self):
        """Test that SCOTCH_randomReset() makes sequences deterministic.

        Matches C test lines 95-115, but uses public API:
        - C test uses: intRandInit(&intranddat), intRandVal(&intranddat, max)
        - We use: SCOTCH_randomReset(), SCOTCH_randomVal(max)

        The behavior is equivalent - both test deterministic sequence generation.
        """
        # Set variant for this test
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

    def test_random_save_load_state(self):
        """Test random state save/load."""
        # Set variant for this test
        import tempfile
        from pathlib import Path
        from pyscotch.graph import c_fopen

        RANDNBR = 100
        INTVALMAX = 10000

        # Reset RNG to known state
        lib.SCOTCH_randomReset()

        # Save RNG state BEFORE generating values
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.rng') as tmpfile:
            tmpfile_path = tmpfile.name

        try:
            # Save initial state
            with c_fopen(tmpfile_path, "w") as file_ptr:
                ret = lib.SCOTCH_randomSave(file_ptr)
                assert ret == 0, "SCOTCH_randomSave failed"

            # Generate first sequence from this state
            randtab1 = [lib.SCOTCH_randomVal(INTVALMAX) for _ in range(RANDNBR)]

            # Load saved state (reset to beginning)
            with c_fopen(tmpfile_path, "r") as file_ptr:
                ret = lib.SCOTCH_randomLoad(file_ptr)
                assert ret == 0, "SCOTCH_randomLoad failed"

            # Generate second sequence - should match first sequence
            randtab2 = [lib.SCOTCH_randomVal(INTVALMAX) for _ in range(RANDNBR)]

            # Verify the sequences match (RNG state was properly saved/restored)
            assert randtab1 == randtab2, "RNG state not properly restored"

        finally:
            Path(tmpfile_path).unlink(missing_ok=True)
