"""
Pytest configuration for PyScotch tests.

Single-Variant Design:
Tests run with ONE Scotch variant, configured via environment variables:
- PYSCOTCH_INT_SIZE: 32 or 64 (default: 32)
- PYSCOTCH_PARALLEL: 0 or 1 (default: 0)

To test all variants, run the test suite multiple times with different configurations:
    PYSCOTCH_INT_SIZE=32 PYSCOTCH_PARALLEL=0 pytest tests/
    PYSCOTCH_INT_SIZE=32 PYSCOTCH_PARALLEL=1 pytest tests/
    PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=0 pytest tests/
    PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=1 pytest tests/

Or use the Makefile targets:
    make test          # Run with default (32-bit sequential)
    make test-all      # Run with all 4 combinations
"""

import os
import pytest


# Read configuration from environment
SCOTCH_INT_SIZE = int(os.environ.get("PYSCOTCH_INT_SIZE", "32"))
SCOTCH_PARALLEL = os.environ.get("PYSCOTCH_PARALLEL", "0") == "1"


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "parallel: mark test as requiring parallel (PT-Scotch) variant"
    )


@pytest.fixture(scope="session")
def scotch_int_size():
    """
    Fixture that provides the current Scotch integer size.

    Returns:
        int: 32 or 64
    """
    return SCOTCH_INT_SIZE


@pytest.fixture(scope="session")
def scotch_parallel():
    """
    Fixture that provides whether parallel variant is loaded.

    Returns:
        bool: True if PT-Scotch (parallel) variant
    """
    return SCOTCH_PARALLEL


def pytest_collection_modifyitems(config, items):
    """Skip tests that require parallel variant if not loaded."""
    if not SCOTCH_PARALLEL:
        skip_parallel = pytest.mark.skip(reason="requires PYSCOTCH_PARALLEL=1")
        for item in items:
            if "parallel" in item.keywords:
                item.add_marker(skip_parallel)
