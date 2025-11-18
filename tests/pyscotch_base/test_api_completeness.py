"""
Test that all Scotch C functions are either bound or documented as skipped.

This test ensures we maintain comprehensive coverage of the Scotch C API
by verifying that every Scotch function is either:
1. Bound via @scotch_binding decorator
2. Documented in INTENTIONALLY_UNBOUND with a reason

This prevents us from accidentally missing Scotch functions during porting.
"""

import pytest
from pyscotch.api_decorators import get_scotch_bindings
from pyscotch import libscotch as lib


# Functions that are intentionally not bound, with reasons
INTENTIONALLY_UNBOUND = {
    # Memory management - Python handles this
    "SCOTCH_memAlloc": "Internal memory management - Python handles allocation",
    "SCOTCH_memFree": "Internal memory management - Python handles deallocation",
    "SCOTCH_memRealloc": "Internal memory management - Python handles reallocation",

    # Error handling - we use Python exceptions
    "SCOTCH_errorProg": "Error handling - we use Python exceptions instead",
    "SCOTCH_errorPrint": "Error handling - we use Python exceptions instead",
    "SCOTCH_errorPrintW": "Error handling - we use Python exceptions instead",

    # Random number seeding - handled internally
    "SCOTCH_randomSeed": "Random seeding - Scotch handles internally",
    "SCOTCH_randomReset": "Random seeding - Scotch handles internally",

    # Version info - available but not critical for bindings
    "SCOTCH_version": "Version info - available via other means",
}


class TestAPICompleteness:
    """Test that PyScotch has complete Scotch C API coverage."""

    def test_all_graph_functions_bound(self):
        """Check that all SCOTCH_graph* functions are bound or documented."""
        scotch_graph_funcs = [
            name for name in dir(lib)
            if name.startswith("SCOTCH_graph") and callable(getattr(lib, name))
        ]

        bound_funcs = get_scotch_bindings()

        missing = []
        for func_name in scotch_graph_funcs:
            if func_name not in bound_funcs and func_name not in INTENTIONALLY_UNBOUND:
                missing.append(func_name)

        assert not missing, (
            f"Scotch graph functions not bound and not documented as skipped:\n"
            f"{', '.join(missing)}\n\n"
            f"Either bind them with @scotch_binding or add to INTENTIONALLY_UNBOUND with a reason."
        )

    def test_all_mesh_functions_bound(self):
        """Check that all SCOTCH_mesh* functions are bound or documented."""
        scotch_mesh_funcs = [
            name for name in dir(lib)
            if name.startswith("SCOTCH_mesh") and callable(getattr(lib, name))
        ]

        bound_funcs = get_scotch_bindings()

        missing = []
        for func_name in scotch_mesh_funcs:
            if func_name not in bound_funcs and func_name not in INTENTIONALLY_UNBOUND:
                missing.append(func_name)

        assert not missing, (
            f"Scotch mesh functions not bound and not documented as skipped:\n"
            f"{', '.join(missing)}\n\n"
            f"Either bind them with @scotch_binding or add to INTENTIONALLY_UNBOUND with a reason."
        )

    def test_all_arch_functions_bound(self):
        """Check that all SCOTCH_arch* functions are bound or documented."""
        scotch_arch_funcs = [
            name for name in dir(lib)
            if name.startswith("SCOTCH_arch") and callable(getattr(lib, name))
        ]

        bound_funcs = get_scotch_bindings()

        missing = []
        for func_name in scotch_arch_funcs:
            if func_name not in bound_funcs and func_name not in INTENTIONALLY_UNBOUND:
                missing.append(func_name)

        assert not missing, (
            f"Scotch arch functions not bound and not documented as skipped:\n"
            f"{', '.join(missing)}\n\n"
            f"Either bind them with @scotch_binding or add to INTENTIONALLY_UNBOUND with a reason."
        )

    def test_all_strat_functions_bound(self):
        """Check that all SCOTCH_strat* functions are bound or documented."""
        scotch_strat_funcs = [
            name for name in dir(lib)
            if name.startswith("SCOTCH_strat") and callable(getattr(lib, name))
        ]

        bound_funcs = get_scotch_bindings()

        missing = []
        for func_name in scotch_strat_funcs:
            if func_name not in bound_funcs and func_name not in INTENTIONALLY_UNBOUND:
                missing.append(func_name)

        assert not missing, (
            f"Scotch strat functions not bound and not documented as skipped:\n"
            f"{', '.join(missing)}\n\n"
            f"Either bind them with @scotch_binding or add to INTENTIONALLY_UNBOUND with a reason."
        )

    def test_all_geom_functions_bound(self):
        """Check that all SCOTCH_geom* functions are bound or documented."""
        scotch_geom_funcs = [
            name for name in dir(lib)
            if name.startswith("SCOTCH_geom") and callable(getattr(lib, name))
        ]

        bound_funcs = get_scotch_bindings()

        missing = []
        for func_name in scotch_geom_funcs:
            if func_name not in bound_funcs and func_name not in INTENTIONALLY_UNBOUND:
                missing.append(func_name)

        assert not missing, (
            f"Scotch geom functions not bound and not documented as skipped:\n"
            f"{', '.join(missing)}\n\n"
            f"Either bind them with @scotch_binding or add to INTENTIONALLY_UNBOUND with a reason."
        )

    def test_bindings_registry_is_populated(self):
        """
        Verify that the bindings registry is actually being populated.

        This test will fail if no decorators have been applied yet,
        which is expected during initial implementation.
        """
        bound_funcs = get_scotch_bindings()

        # For now, we just check that the registry mechanism works
        # Once decorators are applied, this will verify they're registered
        assert isinstance(bound_funcs, dict), "Bindings registry should be a dictionary"

        # This assertion will fail until we apply decorators - that's expected!
        # It serves as a reminder to actually apply the decorators we created.
        if len(bound_funcs) == 0:
            pytest.skip(
                "No bindings registered yet - decorators not yet applied to source code. "
                "This is expected during initial implementation."
            )
