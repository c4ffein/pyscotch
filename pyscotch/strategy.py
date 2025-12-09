"""
Strategy class for PT-Scotch operations.
"""

from ctypes import byref, c_char_p
from typing import Optional

from . import libscotch as lib


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
    """
    Collection of common strategy configurations.

    This class provides convenient presets for partitioning and ordering strategies.
    Most users should use `partition_quality()` or `order_quality()` which delegate
    to Scotch's intelligent built-in defaults.

    Strategy String Syntax:
        - None: Use Scotch's adaptive defaults (recommended for quality)
        - "": Empty string also uses defaults
        - "r": Recursive bisection
        - "m": Multilevel partitioning
        - "n": Nested dissection (for ordering)
        - Complex strings: See Scotch documentation for advanced syntax

    Custom Strategy Examples:
        To use custom strategies with advanced parameters, create a Strategy
        object and set it manually:

        >>> strategy = Strategy()
        >>> # Use Scotch's built-in defaults (recommended)
        >>> partitions = graph.partition(4, strategy)

        >>> # Or specify a custom strategy string
        >>> strategy = Strategy()
        >>> strategy.set_mapping("m{vert=120,low=h{pass=10}f{bal=0.05,move=120}}")
        >>> partitions = graph.partition(4, strategy)

    Note:
        Complex strategy strings follow Scotch's internal syntax. See:
        - external/scotch/src/libscotch/library_graph_map.c (SCOTCH_stratGraphMapBuild)
        - external/scotch/doc/scotch_user*.pdf for strategy documentation
        - Scotch source code for tested examples
    """

    # Partitioning strategies
    DEFAULT_PARTITION = ""
    RECURSIVE_BISECTION = "r"
    MULTILEVEL = "m"
    # None = use Scotch's built-in adaptive defaults (recommended)
    QUALITY_PARTITION = None
    FAST_PARTITION = None

    # Ordering strategies
    DEFAULT_ORDER = ""
    NESTED_DISSECTION = "n"
    SIMPLE_ORDER = "s"
    MINIMUM_FILL = "c"
    # None = use Scotch's built-in adaptive defaults (recommended)
    QUALITY_ORDER = None
    FAST_ORDER = None

    @staticmethod
    def partition_quality() -> Strategy:
        """
        Get a high-quality partitioning strategy.

        Returns a strategy that uses Scotch's built-in adaptive defaults,
        which are optimized for quality over speed.
        """
        strat = Strategy()
        if Strategies.QUALITY_PARTITION is not None:
            strat.set_mapping(Strategies.QUALITY_PARTITION)
        return strat

    @staticmethod
    def partition_fast() -> Strategy:
        """
        Get a fast partitioning strategy.

        Returns a strategy that uses Scotch's built-in adaptive defaults,
        which balance quality and speed.
        """
        strat = Strategy()
        if Strategies.FAST_PARTITION is not None:
            strat.set_mapping(Strategies.FAST_PARTITION)
        return strat

    @staticmethod
    def order_quality() -> Strategy:
        """
        Get a high-quality ordering strategy.

        Returns a strategy that uses Scotch's built-in adaptive defaults,
        which are optimized for quality over speed.
        """
        strat = Strategy()
        if Strategies.QUALITY_ORDER is not None:
            strat.set_ordering(Strategies.QUALITY_ORDER)
        return strat

    @staticmethod
    def order_fast() -> Strategy:
        """
        Get a fast ordering strategy.

        Returns a strategy that uses Scotch's built-in adaptive defaults,
        which balance quality and speed.
        """
        strat = Strategy()
        if Strategies.FAST_ORDER is not None:
            strat.set_ordering(Strategies.FAST_ORDER)
        return strat
