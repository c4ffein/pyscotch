"""
Pytest configuration for PyScotch tests.

Testing PyScotch with different Scotch variants:
- 32-bit vs 64-bit integer sizes
- Sequential vs parallel (PT-Scotch) versions

The multi-variant system allows testing all available variants in a single pytest run!

Usage:

    # Test with all available variants (recommended)
    pytest tests/

    # Test specific variant only (legacy mode)
    PYSCOTCH_INT_SIZE=64 pytest tests/
"""

import os
import pytest


def pytest_configure(config):
    """Register custom markers."""
    # Note: Removed int32/int64/multivariant markers - we don't skip tests based on variants
    # All tests must work with all available variants or fail explicitly
    pass


# Check if environment variable is set (legacy mode)
ENV_INT_SIZE = os.environ.get("PYSCOTCH_INT_SIZE")
if ENV_INT_SIZE:
    # Legacy mode: use environment variable
    SCOTCH_INT_SIZE = int(ENV_INT_SIZE)
    USE_MULTIVARIANT = False
else:
    # Multi-variant mode: test all available variants
    USE_MULTIVARIANT = True
    SCOTCH_INT_SIZE = None  # Will be set per-test


def get_available_variants():
    """Get all available Scotch variants."""
    if USE_MULTIVARIANT:
        import pyscotch.libscotch as lib
        return lib.list_available_variants()
    else:
        # Legacy mode: only one variant (from environment)
        return [(SCOTCH_INT_SIZE, False)]


@pytest.fixture(scope="session")
def scotch_int_size():
    """
    Fixture that provides the current Scotch integer size.

    In multi-variant mode, this returns the active variant's int size.
    In legacy mode, this returns the environment variable value.

    Returns:
        int: 32 or 64
    """
    if USE_MULTIVARIANT:
        import pyscotch.libscotch as lib
        return lib.get_scotch_int_size()
    else:
        return SCOTCH_INT_SIZE


def pytest_generate_tests(metafunc):
    """
    Automatically parameterize tests that use the 'scotch_variant' fixture.

    This enables tests to run with all available Scotch variants automatically.
    """
    if "scotch_variant" in metafunc.fixturenames:
        variants = get_available_variants()

        # Create readable test IDs like "32bit-seq" or "64bit-par"
        ids = [
            f"{int_size}bit-{'par' if parallel else 'seq'}"
            for int_size, parallel in variants
        ]

        metafunc.parametrize("scotch_variant", variants, ids=ids, indirect=True)


@pytest.fixture
def scotch_variant(request):
    """
    Fixture that switches to a specific Scotch variant for the test.

    Tests using this fixture will automatically run with ALL available variants.

    Args:
        request: Pytest request object with variant parameter (int_size, parallel)

    Yields:
        tuple: (int_size, parallel) for the active variant
    """
    int_size, parallel = request.param

    if USE_MULTIVARIANT:
        import pyscotch.libscotch as lib

        # Switch to this variant
        lib.set_active_variant(int_size, parallel)

        # Verify the switch worked
        assert lib.get_scotch_int_size() == int_size, \
            f"Failed to switch to {int_size}-bit variant"

    # Yield the variant info to the test
    yield (int_size, parallel)

    # No cleanup needed - variants stay loaded


# Removed pytest_collection_modifyitems - we don't skip tests based on variants
# Following "no-skip" philosophy: tests must pass or fail explicitly, never skip
