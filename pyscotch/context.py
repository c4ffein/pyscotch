"""
Context class for Scotch threading and option control.
"""

from ctypes import byref

from . import libscotch as lib


class Context:
    """
    A Scotch execution context for controlling threading and options.

    Contexts allow binding graphs/meshes to specific option sets and
    random states, enabling thread-safe parallel use of Scotch.
    """

    def __init__(self):
        """Initialize a new context."""
        self._ctx = lib.SCOTCH_Context()
        ret = lib.SCOTCH_contextInit(byref(self._ctx))
        if ret != 0:
            raise RuntimeError(f"SCOTCH_contextInit failed with error {ret}")
        self._initialized = True

    def __del__(self):
        if hasattr(self, "_initialized") and self._initialized:
            lib.SCOTCH_contextExit(byref(self._ctx))

    def option_get(self, option: int) -> int:
        """
        Get a context option value.

        Args:
            option: Option identifier

        Returns:
            Current option value
        """
        val = lib.SCOTCH_Num()
        ret = lib.SCOTCH_contextOptionGetNum(byref(self._ctx), option, byref(val))
        if ret != 0:
            raise RuntimeError(f"Failed to get context option {option} (error code: {ret})")
        return val.value

    def option_set(self, option: int, value: int) -> None:
        """
        Set a context option value.

        Args:
            option: Option identifier
            value: New option value
        """
        ret = lib.SCOTCH_contextOptionSetNum(byref(self._ctx), option, lib.SCOTCH_Num(value))
        if ret != 0:
            raise RuntimeError(f"Failed to set context option {option} (error code: {ret})")

    def random_clone(self) -> None:
        """Clone the global random state into this context."""
        ret = lib.SCOTCH_contextRandomClone(byref(self._ctx))
        if ret != 0:
            raise RuntimeError(f"Failed to clone random state (error code: {ret})")

    def random_reset(self) -> None:
        """Reset the context's random state."""
        lib.SCOTCH_contextRandomReset(byref(self._ctx))

    def random_seed(self, seed: int) -> None:
        """Set the context's random seed."""
        lib.SCOTCH_contextRandomSeed(byref(self._ctx), lib.SCOTCH_Num(seed))

    def bind_graph(self, source_graph):
        """
        Bind a graph to this context, returning a context-bound graph.

        Args:
            source_graph: Source Graph object

        Returns:
            New Graph object bound to this context
        """
        from .graph import Graph

        bound = Graph()
        ret = lib.SCOTCH_contextBindGraph(
            byref(self._ctx),
            byref(source_graph._graph),
            byref(bound._graph),
        )
        if ret != 0:
            raise RuntimeError(f"Failed to bind graph to context (error code: {ret})")
        return bound
