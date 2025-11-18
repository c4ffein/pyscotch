"""
API level decorators for PyScotch.

These decorators document and track different API levels in PyScotch:

1. @scotch_binding - Direct bindings to Scotch C functions
2. @highlevel_api - High-level Pythonic helpers that wrap Scotch functions
3. @internal_api - Internal implementation details (not public API)

Example usage:
    @scotch_binding("SCOTCH_graphCheck")
    def check(self) -> bool:
        \"\"\"Check the consistency of the graph.\"\"\"
        return lib.SCOTCH_graphCheck(byref(self._graph)) == 0

    @highlevel_api(scotch_functions=["SCOTCH_graphMapInit", "SCOTCH_graphMapCompute", "SCOTCH_graphMapExit"])
    def partition(self, nparts: int, strategy=None) -> np.ndarray:
        \"\"\"Partition the graph into nparts.\"\"\"
        # High-level wrapper implementation

    @internal_api
    def _validate_partition_array(self, parttab, nparts):
        \"\"\"Validate partition array (internal helper).\"\"\"
        # Internal validation logic
"""

from functools import wraps
from typing import Callable, Optional, List

# Global registries for tracking decorated functions
_SCOTCH_BINDINGS = {}  # Maps C function name -> Python function
_HIGHLEVEL_HELPERS = set()  # Set of high-level helper function names
_INTERNAL_HELPERS = set()  # Set of internal helper function names


def scotch_binding(c_function: str, c_signature: Optional[str] = None):
    """
    Mark a method as a direct binding to a Scotch C function.

    This decorator:
    - Registers the binding in _SCOTCH_BINDINGS for completeness checking
    - Augments the docstring with API level information
    - Preserves the original function behavior

    Args:
        c_function: Name of the Scotch C function (e.g., "SCOTCH_graphCheck")
        c_signature: Optional C function signature for documentation

    Returns:
        Decorated function with augmented docstring and metadata

    Example:
        @scotch_binding("SCOTCH_graphCheck")
        def check(self) -> bool:
            \"\"\"Check the consistency of the graph.\"\"\"
            return lib.SCOTCH_graphCheck(byref(self._graph)) == 0
    """
    def decorator(func: Callable) -> Callable:
        # Add metadata attributes
        func._api_level = "scotch_binding"
        func._scotch_function = c_function
        func._scotch_signature = c_signature

        # Register the binding
        _SCOTCH_BINDINGS[c_function] = func

        # Augment docstring with API information
        api_doc = f"\n    **API Level**: Direct Scotch binding\n"
        api_doc += f"    **Maps to**: `{c_function}`\n"
        if c_signature:
            api_doc += f"    **C Signature**: `{c_signature}`\n"

        # TODO: Docstring modification causes segfaults in some cleanup scenarios
        # if func.__doc__:
        #     # Insert API info after the first line (summary line)
        #     lines = func.__doc__.split('\n')
        #     lines.insert(1, api_doc)
        #     func.__doc__ = '\n'.join(lines)
        # else:
        #     func.__doc__ = api_doc

        return func
    return decorator


def highlevel_api(scotch_functions: Optional[List[str]] = None):
    """
    Mark a method as a high-level Pythonic helper.

    This decorator:
    - Registers the function in _HIGHLEVEL_HELPERS
    - Augments the docstring with API level and wrapped functions
    - Documents which Scotch functions this helper wraps

    Args:
        scotch_functions: List of Scotch C function names that this helper wraps

    Returns:
        Decorated function with augmented docstring and metadata

    Example:
        @highlevel_api(scotch_functions=["SCOTCH_graphMapInit", "SCOTCH_graphMapCompute", "SCOTCH_graphMapExit"])
        def partition(self, nparts: int, strategy=None) -> np.ndarray:
            \"\"\"Partition the graph into nparts.\"\"\"
            # Implementation that wraps the low-level Scotch functions
    """
    def decorator(func: Callable) -> Callable:
        # Add metadata attributes
        func._api_level = "highlevel"
        func._wraps_scotch = scotch_functions or []

        # Register the helper
        _HIGHLEVEL_HELPERS.add(func.__name__)

        # Augment docstring with API information
        api_doc = f"\n    **API Level**: High-level helper (Pythonic wrapper)\n"
        if scotch_functions:
            funcs = ", ".join(f"`{f}`" for f in scotch_functions)
            api_doc += f"    **Wraps**: {funcs}\n"

        # TODO: Docstring modification causes segfaults in some cleanup scenarios
        # if func.__doc__:
        #     # Insert API info after the first line (summary line)
        #     lines = func.__doc__.split('\n')
        #     lines.insert(1, api_doc)
        #     func.__doc__ = '\n'.join(lines)
        # else:
        #     func.__doc__ = api_doc

        return func
    return decorator


def internal_api(func: Callable) -> Callable:
    """
    Mark a method as internal implementation detail (not public API).

    This decorator:
    - Registers the function in _INTERNAL_HELPERS
    - Augments the docstring to indicate it's internal
    - Helps document which methods are implementation details

    Args:
        func: The function to mark as internal

    Returns:
        Decorated function with augmented docstring and metadata

    Example:
        @internal_api
        def _validate_partition_array(self, parttab, nparts):
            \"\"\"Validate partition array (internal helper).\"\"\"
            # Internal validation logic
    """
    # Add metadata attribute
    func._api_level = "internal"

    # Register the helper
    _INTERNAL_HELPERS.add(func.__name__)

    # Augment docstring with API information
    api_doc = "\n    **API Level**: Internal implementation (not public API)\n"

    # TODO: Docstring modification causes segfaults in some cleanup scenarios
    # Temp fix by not defining this
    # if func.__doc__:
    #     # Insert API info after the first line (summary line)
    #     lines = func.__doc__.split('\n')
    #     lines.insert(1, api_doc)
    #     func.__doc__ = '\n'.join(lines)
    # else:
    #     func.__doc__ = api_doc

    return func


# Public API for accessing registries
def get_scotch_bindings():
    """
    Get all registered Scotch C function bindings.

    Returns:
        Dictionary mapping Scotch C function names to Python functions
    """
    return _SCOTCH_BINDINGS.copy()


def get_highlevel_helpers():
    """
    Get all registered high-level helpers.

    Returns:
        Set of high-level helper function names
    """
    return _HIGHLEVEL_HELPERS.copy()


def get_internal_helpers():
    """
    Get all registered internal helpers.

    Returns:
        Set of internal helper function names
    """
    return _INTERNAL_HELPERS.copy()
