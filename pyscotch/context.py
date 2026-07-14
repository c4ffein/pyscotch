"""
Context class for Scotch threading and option control.
"""

from ctypes import byref

from .api_decorators import scotch_binding
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
            raise lib.scotch_error("SCOTCH_contextInit failed", ret)
        self._initialized = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @scotch_binding("SCOTCH_contextExit", "void SCOTCH_contextExit(SCOTCH_Context *)")
    def close(self):
        """Release context resources. Called automatically when used as a context manager."""
        if getattr(self, "_initialized", False):
            lib.SCOTCH_contextExit(byref(self._ctx))
            self._initialized = False

    @scotch_binding(
        "SCOTCH_contextOptionGetNum",
        "int SCOTCH_contextOptionGetNum(SCOTCH_Context *, const int, SCOTCH_Num *)",
    )
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
            raise lib.scotch_error(f"Failed to get context option {option}", ret)
        return val.value

    @scotch_binding(
        "SCOTCH_contextOptionSetNum",
        "int SCOTCH_contextOptionSetNum(SCOTCH_Context *, const int, SCOTCH_Num)",
    )
    def option_set(self, option: int, value: int) -> None:
        """
        Set a context option value.

        Args:
            option: Option identifier
            value: New option value
        """
        ret = lib.SCOTCH_contextOptionSetNum(byref(self._ctx), option, lib.SCOTCH_Num(value))
        if ret != 0:
            raise lib.scotch_error(f"Failed to set context option {option}", ret)

    @scotch_binding("SCOTCH_contextRandomClone", "int SCOTCH_contextRandomClone(SCOTCH_Context *)")
    def random_clone(self) -> None:
        """Clone the global random state into this context."""
        ret = lib.SCOTCH_contextRandomClone(byref(self._ctx))
        if ret != 0:
            raise lib.scotch_error("Failed to clone random state", ret)

    @scotch_binding("SCOTCH_contextRandomReset", "void SCOTCH_contextRandomReset(SCOTCH_Context *)")
    def random_reset(self) -> None:
        """Reset the context's random state."""
        lib.SCOTCH_contextRandomReset(byref(self._ctx))

    @scotch_binding(
        "SCOTCH_contextRandomSeed", "void SCOTCH_contextRandomSeed(SCOTCH_Context *, SCOTCH_Num)"
    )
    def random_seed(self, seed: int) -> None:
        """Set the context's random seed."""
        lib.SCOTCH_contextRandomSeed(byref(self._ctx), lib.SCOTCH_Num(seed))

    @scotch_binding(
        "SCOTCH_contextBindGraph",
        "int SCOTCH_contextBindGraph(SCOTCH_Context *, const SCOTCH_Graph *, SCOTCH_Graph *)",
    )
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
            raise lib.scotch_error("Failed to bind graph to context", ret)
        return bound
