"""
Strategy class for PT-Scotch operations.
"""

from ctypes import byref, c_char_p
from typing import Optional

try:
    from . import libscotch as lib
    _lib_available = lib._lib_sequential is not None
except ImportError:
    _lib_available = False


class Strategy:
    """
    Represents a strategy for graph operations (partitioning, ordering, etc.).

    Strategies control how Scotch performs operations like graph partitioning
    and ordering. They can be customized with strategy strings or use defaults.
    """

    def __init__(self, strategy_string: Optional[str] = None):
        """
        Initialize a strategy.

        Args:
            strategy_string: Optional strategy string in Scotch format
        """
        if not _lib_available:
            raise RuntimeError(
                "Scotch library not available. Build it with 'make build-scotch'"
            )

        self._strat = lib.SCOTCH_Strat()
        ret = lib.SCOTCH_stratInit(byref(self._strat))
        if ret != 0:
            raise RuntimeError(f"Failed to initialize strategy (error code: {ret})")

        self._initialized = True
        self._strategy_string = strategy_string

    def __del__(self):
        """Clean up strategy resources."""
        if hasattr(self, "_initialized") and self._initialized:
            lib.SCOTCH_stratExit(byref(self._strat))

    def set_mapping(self, strategy_string: str) -> None:
        """
        Set a mapping/partitioning strategy from a string.

        Args:
            strategy_string: Strategy string in Scotch format

        Raises:
            RuntimeError: If setting the strategy fails

        Strategy string format examples:
            - "": Use default strategy
            - "r": Use recursive bisection
            - "m{vert=100,low=h{pass=10},asc=b{width=3}}": Custom strategy
        """
        ret = lib.SCOTCH_stratGraphMap(
            byref(self._strat),
            c_char_p(strategy_string.encode("utf-8"))
        )
        if ret != 0:
            raise RuntimeError(f"Failed to set mapping strategy (error code: {ret})")
        self._strategy_string = strategy_string

    def set_ordering(self, strategy_string: str) -> None:
        """
        Set an ordering strategy from a string.

        Args:
            strategy_string: Strategy string in Scotch format

        Raises:
            RuntimeError: If setting the strategy fails

        Strategy string format examples:
            - "": Use default strategy
            - "n": Nested dissection
            - "s": Simple ordering
            - "c": Minimum fill ordering
        """
        ret = lib.SCOTCH_stratGraphOrder(
            byref(self._strat),
            c_char_p(strategy_string.encode("utf-8"))
        )
        if ret != 0:
            raise RuntimeError(f"Failed to set ordering strategy (error code: {ret})")
        self._strategy_string = strategy_string

    def set_ordering_default(self) -> None:
        """Set the default ordering strategy."""
        self.set_ordering("")

    def set_mapping_default(self) -> None:
        """Set the default mapping/partitioning strategy."""
        self.set_mapping("")

    def set_recursive_bisection(self) -> None:
        """Set recursive bisection strategy for partitioning."""
        self.set_mapping("r")

    def set_multilevel(self) -> None:
        """Set multilevel strategy for partitioning."""
        self.set_mapping("m")

    def set_nested_dissection(self) -> None:
        """Set nested dissection strategy for ordering."""
        self.set_ordering("n")

    @property
    def strategy_string(self) -> Optional[str]:
        """Get the current strategy string."""
        return self._strategy_string


# Pre-defined strategy configurations
class Strategies:
    """Collection of common strategy configurations."""

    # Partitioning strategies
    DEFAULT_PARTITION = ""
    RECURSIVE_BISECTION = "r"
    MULTILEVEL = "m"
    QUALITY_PARTITION = "m{vert=100,low=h{pass=10},asc=b{bnd=f{bal=0.05},org=f{bal=0.05}}}"
    FAST_PARTITION = "m{vert=1000,low=h{pass=5}}"

    # Ordering strategies
    DEFAULT_ORDER = ""
    NESTED_DISSECTION = "n"
    SIMPLE_ORDER = "s"
    MINIMUM_FILL = "c"
    QUALITY_ORDER = "n{sep=/((vert>1000)?m{vert=100,low=h{pass=10}}:)})"
    FAST_ORDER = "s"

    @staticmethod
    def partition_quality() -> Strategy:
        """Get a high-quality partitioning strategy."""
        strat = Strategy()
        strat.set_mapping(Strategies.QUALITY_PARTITION)
        return strat

    @staticmethod
    def partition_fast() -> Strategy:
        """Get a fast partitioning strategy."""
        strat = Strategy()
        strat.set_mapping(Strategies.FAST_PARTITION)
        return strat

    @staticmethod
    def order_quality() -> Strategy:
        """Get a high-quality ordering strategy."""
        strat = Strategy()
        strat.set_ordering(Strategies.QUALITY_ORDER)
        return strat

    @staticmethod
    def order_fast() -> Strategy:
        """Get a fast ordering strategy."""
        strat = Strategy()
        strat.set_ordering(Strategies.FAST_ORDER)
        return strat
