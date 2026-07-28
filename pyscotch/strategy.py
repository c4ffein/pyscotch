"""
Strategy class for PT-Scotch operations.
"""

from contextlib import contextmanager
from ctypes import byref, c_char_p
from enum import IntFlag
from typing import Optional

from .api_decorators import scotch_binding, highlevel_api, internal_api
from . import libscotch as lib


class StrategyFlags(IntFlag):
    """Strategy characteristic flags for SCOTCH_strat*Build functions.

    Values mirror the SCOTCH_STRAT* constants in Scotch's library.h exactly —
    nothing added, nothing renamed. They are part of Scotch's public API and
    stable across versions.
    """

    DEFAULT = 0x00000
    QUALITY = 0x00001
    SPEED = 0x00002
    BALANCE = 0x00004
    SAFETY = 0x00008
    SCALABILITY = 0x00010
    RECURSIVE = 0x00100
    REMAP = 0x00200
    LEVEL_MAX = 0x01000
    LEVEL_MIN = 0x02000
    LEAF_SIMPLE = 0x04000
    SEPA_SIMPLE = 0x08000
    DISCONNECTED = 0x10000


#: Upstream default imbalance ratios, from the implicit default-strategy
#: builds in library_graph_map.c (mapping), library_graph_part_ovl.c
#: (overlap partitioning) and library_graph_order.c (ordering). Each family
#: has its OWN default; a request with balance=None resolves to the constant
#: of the operation that consumes it.
_DEFAULT_MAPPING_BALANCE = 0.01
_DEFAULT_OVERLAP_BALANCE = 0.05
_DEFAULT_ORDERING_BALANCE = 0.2


@contextmanager
def _ephemeral_strat():
    """A freshly initialized SCOTCH_Strat, freed when the block exits.

    Building one costs ~100 microseconds — negligible next to any operation
    that consumes it — which is what makes per-call builds affordable.
    """
    strat = lib.SCOTCH_Strat()
    ret = lib.SCOTCH_stratInit(byref(strat))
    if ret != 0:
        raise lib.scotch_error("Failed to initialize strategy", ret)
    try:
        yield strat
    finally:
        lib.SCOTCH_stratExit(byref(strat))


class Strategy:
    """
    Represents a strategy for graph operations (partitioning, ordering, etc.).

    Strategies control how Scotch performs operations like graph partitioning
    and ordering. They can be customized with strategy strings or use defaults.

    A freshly created Strategy *is* Scotch's default: when the underlying
    SCOTCH_Strat is still empty at compute time, Scotch builds its adaptive
    default strategy for the operation at hand.

    Some configurations cannot be built at creation time: flag-based mapping
    strategies (see request_mapping) need the number of parts, which is only
    known when the strategy is used. Such requests are recorded on the Strategy
    and built by the operation that consumes it (e.g. Graph.partition) into a
    private per-call strat. Using a Strategy therefore never mutates it: one
    Strategy can be shared across part counts and across threads. An operation
    that cannot honour a recorded request raises instead of silently ignoring
    it.

    For tight loops where the per-call build matters, built_for_mapping /
    built_for_ordering / built_for_overlap materialize the strategy once into
    a BuiltStrategy handle that is reused (and cross-checked) inside its
    with-block.
    """

    def __init__(self, strategy_string: Optional[str] = None):
        """
        Initialize a strategy.

        Args:
            strategy_string: Optional strategy string in Scotch format. The
                string is applied by the operation the strategy is used with
                (mapping strings and ordering strings have different grammars,
                so it cannot be parsed before the target operation is known).
                An empty string (or None) selects Scotch's default strategy.
        """
        self._strat_data = lib.SCOTCH_Strat()
        ret = lib.SCOTCH_stratInit(byref(self._strat_data))
        if ret != 0:
            raise lib.scotch_error("Failed to initialize strategy", ret)

        self._initialized = True
        # Deferred configuration, built into a private per-call strat by the
        # consuming operation (the Strategy itself is never mutated by use):
        #   ("string", s)                            -> parsed by the target op
        #   ("map_flags", flags, balance, nparts)    -> SCOTCH_stratGraphMapBuild
        #   ("order_flags", flags, levels, balance)  -> SCOTCH_stratGraphOrderBuild
        self._pending = None
        # True once a set_*/build_* method has built a strategy into
        # _strat_data; False means _strat_data is still empty.
        self._configured = False
        self._strategy_string = strategy_string
        if strategy_string:  # "" and None both mean "Scotch's default"
            self._pending = ("string", strategy_string)

    @property
    def _strat(self):
        """The underlying SCOTCH_Strat, for operations to pass to libscotch.

        Guards against an operation consuming a strategy whose recorded request
        it never built: silently using the (empty, i.e. default) underlying
        strat would reintroduce the do-nothing-strategy class of bug.
        """
        if self._pending is not None:
            kind = self._pending[0]
            what = (
                f"the strategy string {self._pending[1]!r}"
                if kind == "string"
                else "a flag-based build request"
            )
            raise RuntimeError(
                f"This Strategy carries {what} that the current operation does "
                "not know how to build. Configure the strategy explicitly with "
                "set_mapping()/set_ordering() (or their dgraph variants) instead."
            )
        return self._strat_data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _reinit(self):
        """Give the underlying strat a fresh (empty) state, keeping bookkeeping."""
        if self._initialized:
            lib.SCOTCH_stratExit(byref(self._strat_data))
            self._initialized = False
        ret = lib.SCOTCH_stratInit(byref(self._strat_data))
        if ret != 0:
            raise lib.scotch_error("Failed to reinitialize strategy", ret)
        self._initialized = True

    @scotch_binding("SCOTCH_stratExit", "void SCOTCH_stratExit(SCOTCH_Strat *)")
    def close(self):
        """Release strategy resources. Called automatically when used as a context manager."""
        if getattr(self, "_initialized", False):
            lib.SCOTCH_stratExit(byref(self._strat_data))
            self._initialized = False

    @scotch_binding(
        "SCOTCH_stratGraphMap", "int SCOTCH_stratGraphMap(SCOTCH_Strat *, const char *)"
    )
    def set_mapping(self, strategy_string: str) -> None:
        """
        Set a mapping/partitioning strategy from a string.

        Args:
            strategy_string: Strategy string in Scotch format

        Raises:
            RuntimeError: If setting the strategy fails

        Strategy string format examples:
            - "": Use the default strategy
            - "r{sep=gf}": Recursive bisection, greedy-growing + FM bipartitioning
            - "m{vert=100,low=r{sep=gf},asc=f}": Custom multilevel strategy

        Note:
            PyScotch treats "" as "Scotch's default strategy". (At the raw C
            level an empty string builds a do-nothing method that leaves every
            vertex unassigned — a trap with no legitimate use.) Also beware
            that sub-strategies left implicit — bare "r", "m", or "r{bal=0.05}"
            — default to a do-nothing dummy in the string grammar, putting
            every vertex into one part. Spell out the sub-strategy (e.g.
            "r{sep=gf}") or use set_recursive_bisection()/request_mapping().
        """
        if strategy_string == "":
            self.reset()
            self._strategy_string = ""
            return
        ret = lib.SCOTCH_stratGraphMap(
            byref(self._strat_data), c_char_p(strategy_string.encode("utf-8"))
        )
        if ret != 0:
            raise lib.scotch_error("Failed to set mapping strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = strategy_string

    @scotch_binding(
        "SCOTCH_stratGraphOrder", "int SCOTCH_stratGraphOrder(SCOTCH_Strat *, const char *)"
    )
    def set_ordering(self, strategy_string: str) -> None:
        """
        Set an ordering strategy from a string.

        Args:
            strategy_string: Strategy string in Scotch format

        Raises:
            RuntimeError: If setting the strategy fails

        Strategy string format examples:
            - "": Use the default strategy
            - "s": Simple (natural-order) ordering

        Note:
            PyScotch treats "" as "Scotch's default strategy" (see set_mapping).
            Bare method codes like "n" or "c" are *incomplete* strategies that
            return the identity permutation — no reordering at all. Use
            set_nested_dissection() or full parameterized strings instead.
            ("s" alone is fine: the natural order is exactly what it means.)
        """
        if strategy_string == "":
            self.reset()
            self._strategy_string = ""
            return
        ret = lib.SCOTCH_stratGraphOrder(
            byref(self._strat_data), c_char_p(strategy_string.encode("utf-8"))
        )
        if ret != 0:
            raise lib.scotch_error("Failed to set ordering strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = strategy_string

    @scotch_binding(
        "SCOTCH_stratGraphPartOvl",
        "int SCOTCH_stratGraphPartOvl(SCOTCH_Strat *, const char *)",
    )
    def set_overlap_partitioning(self, strategy_string: str) -> None:
        """
        Set an overlap-partitioning strategy from a string.

        Overlap partitioning (Graph.partition_overlap) uses its own strategy
        grammar, distinct from plain mapping strategies.

        Args:
            strategy_string: Overlap partitioning strategy string in Scotch
                format; "" selects the default strategy.

        Raises:
            RuntimeError: If setting the strategy fails
        """
        if strategy_string == "":
            self.reset()
            self._strategy_string = ""
            return
        ret = lib.SCOTCH_stratGraphPartOvl(
            byref(self._strat_data), c_char_p(strategy_string.encode("utf-8"))
        )
        if ret != 0:
            raise lib.scotch_error("Failed to set overlap partitioning strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = strategy_string

    @scotch_binding(
        "SCOTCH_stratDgraphMap", "int SCOTCH_stratDgraphMap(SCOTCH_Strat *, const char *)"
    )
    def set_dgraph_mapping(self, strategy_string: str) -> None:
        """
        Set a parallel (PT-Scotch) mapping/partitioning strategy from a string.

        Requires the parallel variant (PYSCOTCH_PARALLEL=1).

        Args:
            strategy_string: Parallel mapping strategy string in Scotch format

        Raises:
            RuntimeError: If setting the strategy fails

        Note:
            PyScotch treats "" as "PT-Scotch's default strategy", exactly like
            set_mapping. (At the raw C level an empty string builds a
            do-nothing method — SCOTCH_dgraphMap only builds the real default
            when the strategy is still untouched — so "" would silently put
            every vertex into one part.)
        """
        if strategy_string == "":
            self.reset()
            self._strategy_string = ""
            return
        ret = lib.SCOTCH_stratDgraphMap(
            byref(self._strat_data), c_char_p(strategy_string.encode("utf-8"))
        )
        if ret != 0:
            raise lib.scotch_error("Failed to set parallel mapping strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = strategy_string

    @scotch_binding(
        "SCOTCH_stratDgraphOrder", "int SCOTCH_stratDgraphOrder(SCOTCH_Strat *, const char *)"
    )
    def set_dgraph_ordering(self, strategy_string: str) -> None:
        """
        Set a parallel (PT-Scotch) ordering strategy from a string.

        Requires the parallel variant (PYSCOTCH_PARALLEL=1).

        Args:
            strategy_string: Parallel ordering strategy string in Scotch format

        Raises:
            RuntimeError: If setting the strategy fails

        Note:
            PyScotch treats "" as "PT-Scotch's default strategy", exactly like
            set_ordering. (At the raw C level an empty string builds a
            do-nothing method, so "" would silently return the identity
            permutation — no reordering at all.)
        """
        if strategy_string == "":
            self.reset()
            self._strategy_string = ""
            return
        ret = lib.SCOTCH_stratDgraphOrder(
            byref(self._strat_data), c_char_p(strategy_string.encode("utf-8"))
        )
        if ret != 0:
            raise lib.scotch_error("Failed to set parallel ordering strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = strategy_string

    @scotch_binding(
        "SCOTCH_stratDgraphMapBuild",
        "int SCOTCH_stratDgraphMapBuild(SCOTCH_Strat *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, double)",
    )
    def build_dgraph_mapping(
        self, flagval: int, procnbr: int, partnbr: int, kbalval: float
    ) -> None:
        """
        Build a parallel mapping strategy from high-level parameters.

        Args:
            flagval: Strategy characteristics flags (StrategyFlags, 0 for defaults)
            procnbr: Number of processes the strategy will run on
            partnbr: Number of expected parts/domains
            kbalval: Desired imbalance ratio (e.g. 0.05)

        Raises:
            RuntimeError: If building the strategy fails
        """
        ret = lib.SCOTCH_stratDgraphMapBuild(
            byref(self._strat_data),
            lib.SCOTCH_Num(flagval),
            lib.SCOTCH_Num(procnbr),
            lib.SCOTCH_Num(partnbr),
            float(kbalval),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to build parallel mapping strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = None

    @scotch_binding(
        "SCOTCH_stratDgraphClusterBuild",
        "int SCOTCH_stratDgraphClusterBuild(SCOTCH_Strat *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, double, double)",
    )
    def build_dgraph_clustering(
        self, flagval: int, procnbr: int, pwgtval: int, densval: float, bbalval: float
    ) -> None:
        """
        Build a parallel clustering strategy from high-level parameters.

        Args:
            flagval: Strategy characteristics flags (StrategyFlags, 0 for defaults)
            procnbr: Number of processes the strategy will run on
            pwgtval: Threshold cluster load
            densval: Threshold cluster density value
            bbalval: Maximum imbalance ratio

        Raises:
            RuntimeError: If building the strategy fails
        """
        ret = lib.SCOTCH_stratDgraphClusterBuild(
            byref(self._strat_data),
            lib.SCOTCH_Num(flagval),
            lib.SCOTCH_Num(procnbr),
            lib.SCOTCH_Num(pwgtval),
            float(densval),
            float(bbalval),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to build parallel clustering strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = None

    @scotch_binding(
        "SCOTCH_stratDgraphOrderBuild",
        "int SCOTCH_stratDgraphOrderBuild(SCOTCH_Strat *, SCOTCH_Num, SCOTCH_Num, SCOTCH_Num, double)",
    )
    def build_dgraph_ordering(
        self, flagval: int, procnbr: int, levlnbr: int, balrat: float
    ) -> None:
        """
        Build a parallel ordering strategy from high-level parameters.

        Args:
            flagval: Strategy characteristics flags (StrategyFlags, 0 for defaults)
            procnbr: Number of processes the strategy will run on
            levlnbr: Number of nested dissection levels (0 for default)
            balrat: Desired imbalance ratio (e.g. 0.2)

        Raises:
            RuntimeError: If building the strategy fails
        """
        ret = lib.SCOTCH_stratDgraphOrderBuild(
            byref(self._strat_data),
            lib.SCOTCH_Num(flagval),
            lib.SCOTCH_Num(procnbr),
            lib.SCOTCH_Num(levlnbr),
            float(balrat),
        )
        if ret != 0:
            raise lib.scotch_error("Failed to build parallel ordering strategy", ret)
        self._pending = None
        self._configured = True
        self._strategy_string = None

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphMapBuild"])
    def request_mapping(
        self,
        flags: StrategyFlags = StrategyFlags.DEFAULT,
        balance: Optional[float] = None,
        nparts: Optional[int] = None,
    ) -> None:
        """Request a mapping strategy built from characteristic flags.

        The strategy is built with SCOTCH_stratGraphMapBuild into a private
        per-call strat by the operation that uses it (e.g. Graph.partition):
        building needs the number of parts, which the operation knows. The
        Strategy itself is never mutated by use, so one Strategy can be
        shared freely across part counts and across threads.

        Args:
            flags: Combination of StrategyFlags characteristics
                (e.g. StrategyFlags.QUALITY | StrategyFlags.SAFETY).
            balance: Desired imbalance ratio. None (the default) means the
                consuming operation's own upstream default: 0.01 for
                mapping/partitioning, 0.05 for overlap partitioning — the
                same values Scotch uses when building its implicit default
                strategy for that operation.
            nparts: Optional pin, mirroring the C API where the part count is
                fixed at SCOTCH_stratGraphMapBuild time. When set, consuming
                operations must be called with this exact part count; a
                mismatch raises instead of silently mistuning. None (the
                default) tunes the build to each call's actual part count.
        """
        self._pending = (
            "map_flags",
            int(flags),
            None if balance is None else float(balance),
            None if nparts is None else int(nparts),
        )
        self._strategy_string = None

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphOrderBuild"])
    def request_ordering(
        self,
        flags: StrategyFlags = StrategyFlags.DEFAULT,
        levels: int = 0,
        balance: Optional[float] = None,
    ) -> None:
        """Request an ordering strategy built from characteristic flags.

        The strategy is built with SCOTCH_stratGraphOrderBuild into a private
        per-call strat by the ordering operation that uses it; like
        request_mapping, the Strategy itself is never mutated by use.

        Args:
            flags: Combination of StrategyFlags characteristics.
            levels: Number of nested dissection levels, for
                StrategyFlags.LEVEL_MAX / LEVEL_MIN (0 otherwise).
            balance: Desired imbalance ratio. None (the default) means the
                upstream default for ordering, 0.2.
        """
        self._pending = ("order_flags", int(flags), int(levels), None if balance is None else float(balance))
        self._strategy_string = None

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphMapBuild"])
    @contextmanager
    def built_for_mapping(self, nparts: int):
        """Materialize this strategy once for repeated mapping/partitioning.

        Yields a BuiltStrategy valid inside the with-block: passing it to
        Graph.partition skips the per-call build (~100 microseconds) that
        plain Strategy consumption performs — worth it only in tight loops
        over small graphs. The part count stays explicit at every call site
        and is cross-checked against the handle.

        Not thread-safe: share the (immutable) Strategy across threads and
        materialize per thread instead.
        """
        with self._materialized_mapping(nparts) as stratdat:
            built = BuiltStrategy(stratdat, "mapping", int(nparts))
            try:
                yield built
            finally:
                built._active = False

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphOrderBuild"])
    @contextmanager
    def built_for_ordering(self):
        """Materialize this strategy once for repeated ordering use.

        See built_for_mapping for the semantics; ordering strategies carry no
        part count, so only the operation family is checked.
        """
        with self._materialized_ordering() as stratdat:
            built = BuiltStrategy(stratdat, "ordering", None)
            try:
                yield built
            finally:
                built._active = False

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphPartOvlBuild"])
    @contextmanager
    def built_for_overlap(self, nparts: int):
        """Materialize this strategy once for repeated overlap partitioning.

        See built_for_mapping for the semantics. Overlap partitioning has its
        own strategy grammar, so a mapping handle and an overlap handle built
        from the same Strategy are different compiled objects.
        """
        with self._materialized_overlap(nparts) as stratdat:
            built = BuiltStrategy(stratdat, "overlap", int(nparts))
            try:
                yield built
            finally:
                built._active = False

    def _check_nparts_pin(self, nparts: int) -> None:
        pin = self._pending[3]
        if pin is not None and int(nparts) != pin:
            raise ValueError(
                f"This Strategy was requested for nparts={pin} "
                f"(request_mapping(nparts=...)); it cannot be used with "
                f"{nparts} parts."
            )

    @contextmanager
    def _materialized_mapping(self, nparts: int):
        """Yield the SCOTCH_Strat a mapping/partitioning operation must use.

        Deferred configuration (constructor strings, request_mapping) is
        built into a private per-call strat tuned to this call's nparts and
        freed on exit — the Strategy itself is never mutated by use, which is
        what makes sharing one Strategy across threads and part counts safe.
        A never-configured default Strategy also yields a private empty strat,
        so Scotch's implicit-default build (which caches itself into the strat
        it is handed) cannot leak into the shared object either.
        """
        if self._pending is None:
            if self._configured:
                yield self._strat_data
            else:
                with _ephemeral_strat() as strat:
                    yield strat
            return
        kind = self._pending[0]
        if kind == "string":
            # The pending string is re-parsed per call and never cleared, so
            # a bad string re-raises on EVERY use instead of silently running
            # the default strategy.
            with _ephemeral_strat() as strat:
                ret = lib.SCOTCH_stratGraphMap(
                    byref(strat), c_char_p(self._pending[1].encode("utf-8"))
                )
                if ret != 0:
                    raise lib.scotch_error("Failed to set mapping strategy", ret)
                yield strat
        elif kind == "map_flags":
            _, flags, balance, _pin = self._pending
            self._check_nparts_pin(nparts)
            if balance is None:
                balance = _DEFAULT_MAPPING_BALANCE
            with _ephemeral_strat() as strat:
                ret = lib.SCOTCH_stratGraphMapBuild(
                    byref(strat),
                    lib.SCOTCH_Num(flags),
                    lib.SCOTCH_Num(nparts),
                    float(balance),
                )
                if ret != 0:
                    raise lib.scotch_error(
                        f"Failed to build mapping strategy (flags={flags:#x})", ret
                    )
                yield strat
        else:
            raise RuntimeError(
                "This Strategy holds an ordering request (request_ordering); "
                "it cannot be used for partitioning/mapping."
            )

    @contextmanager
    def _materialized_ordering(self):
        """Yield the SCOTCH_Strat an ordering operation must use.

        See _materialized_mapping for the per-call build semantics.
        """
        if self._pending is None:
            if self._configured:
                yield self._strat_data
            else:
                with _ephemeral_strat() as strat:
                    yield strat
            return
        kind = self._pending[0]
        if kind == "string":
            # See _materialized_mapping: a bad string re-raises on every use.
            with _ephemeral_strat() as strat:
                ret = lib.SCOTCH_stratGraphOrder(
                    byref(strat), c_char_p(self._pending[1].encode("utf-8"))
                )
                if ret != 0:
                    raise lib.scotch_error("Failed to set ordering strategy", ret)
                yield strat
        elif kind == "order_flags":
            _, flags, levels, balance = self._pending
            if balance is None:
                balance = _DEFAULT_ORDERING_BALANCE
            with _ephemeral_strat() as strat:
                ret = lib.SCOTCH_stratGraphOrderBuild(
                    byref(strat),
                    lib.SCOTCH_Num(flags),
                    lib.SCOTCH_Num(levels),
                    float(balance),
                )
                if ret != 0:
                    raise lib.scotch_error(
                        f"Failed to build ordering strategy (flags={flags:#x})", ret
                    )
                yield strat
        else:
            raise RuntimeError(
                "This Strategy holds a mapping request (request_mapping); "
                "it cannot be used for ordering."
            )

    @contextmanager
    def _materialized_overlap(self, nparts: int):
        """Yield the SCOTCH_Strat an overlap-partitioning operation must use.

        See _materialized_mapping for the per-call build semantics.
        """
        if self._pending is None:
            if self._configured:
                yield self._strat_data
            else:
                with _ephemeral_strat() as strat:
                    yield strat
            return
        kind = self._pending[0]
        if kind == "string":
            # See _materialized_mapping: a bad string re-raises on every use.
            with _ephemeral_strat() as strat:
                ret = lib.SCOTCH_stratGraphPartOvl(
                    byref(strat), c_char_p(self._pending[1].encode("utf-8"))
                )
                if ret != 0:
                    raise lib.scotch_error(
                        "Failed to set overlap partitioning strategy", ret
                    )
                yield strat
        elif kind == "map_flags":
            _, flags, balance, _pin = self._pending
            self._check_nparts_pin(nparts)
            if balance is None:
                balance = _DEFAULT_OVERLAP_BALANCE
            with _ephemeral_strat() as strat:
                ret = lib.SCOTCH_stratGraphPartOvlBuild(
                    byref(strat),
                    lib.SCOTCH_Num(flags),
                    lib.SCOTCH_Num(nparts),
                    float(balance),
                )
                if ret != 0:
                    raise lib.scotch_error(
                        f"Failed to build overlap partitioning strategy (flags={flags:#x})", ret
                    )
                yield strat
        else:
            raise RuntimeError(
                "This Strategy holds an ordering request (request_ordering); "
                "it cannot be used for overlap partitioning."
            )

    @highlevel_api(scotch_functions=["SCOTCH_stratInit", "SCOTCH_stratExit"])
    def reset(self) -> None:
        """Return the strategy to its initial (Scotch default) state.

        This is the one canonical "back to default" spelling: the default is
        the empty state, which is family-agnostic — each consuming operation
        builds its own default from it. (The string setters accept "" as a
        synonym, for string-driven configuration paths.)

        The C-level reinit matters: a tree explicitly built by a set_* call
        must be freed here — no later build would free it, and dgraph/mesh
        operations consume the underlying strat directly.
        """
        self._reinit()
        self._pending = None
        self._configured = False
        self._strategy_string = None

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphMapBuild"])
    def set_recursive_bisection(self) -> None:
        """Set recursive bisection strategy for partitioning.

        Built via SCOTCH_stratGraphMapBuild(StrategyFlags.RECURSIVE): the bare
        strategy string "r" is incomplete (it puts every vertex in one part).

        Warning:
            The flag-based build is a workaround for that upstream string
            behaviour. The selected strategy itself is genuine pure recursive
            bipartitioning; if a future Scotch release fixes the string
            grammar, the implementation here may change, but the behaviour
            should not.
        """
        self.request_mapping(StrategyFlags.RECURSIVE)

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphMapBuild"])
    def set_multilevel(self) -> None:
        """Set multilevel strategy for partitioning.

        Scotch's default strategy *is* multilevel (there is no MULTILEVEL flag
        in the SCOTCH_strat*Build API), so this requests the default build.
        The bare strategy string "m" is incomplete and must not be used: it
        puts every vertex in one part.

        Warning:
            Workaround — upstream currently offers no way to select
            "multilevel" as a distinct choice, so this method is an alias of
            the default build, kept for compatibility with the released API.
            It could be considered broken in the sense that it selects nothing
            beyond the default. Pending the upstream questions in
            QUESTIONS_FOR_SCOTCH_TEAM.md, it may change or be deprecated in a
            future release; prefer a plain ``Strategy()`` (or
            ``request_mapping(StrategyFlags.DEFAULT)``) to state that intent
            exactly.
        """
        self.request_mapping(StrategyFlags.DEFAULT)

    @highlevel_api(scotch_functions=["SCOTCH_stratGraphOrderBuild"])
    def set_nested_dissection(self) -> None:
        """Set nested dissection strategy for ordering.

        Scotch's default ordering *is* nested-dissection based, so this
        requests the default build. The bare strategy string "n" is incomplete
        and must not be used: it returns the identity permutation (no
        reordering at all).

        Warning:
            Workaround — upstream currently offers no way to select nested
            dissection as a distinct choice, so this method is an alias of
            the default build, kept for compatibility with the released API.
            It could be considered broken in the sense that it selects nothing
            beyond the default. Pending the upstream questions in
            QUESTIONS_FOR_SCOTCH_TEAM.md, it may change or be deprecated in a
            future release; prefer a plain ``Strategy()`` (or
            ``request_ordering(StrategyFlags.DEFAULT)``) to state that intent
            exactly.
        """
        self.request_ordering(StrategyFlags.DEFAULT)

    @property
    @internal_api
    def strategy_string(self) -> Optional[str]:
        """Get the current strategy string (None for flag-built strategies)."""
        return self._strategy_string


# Pre-defined strategy configurations
class BuiltStrategy:
    """A strategy materialized for one operation family — and, for the
    partitioning families, one part count.

    Obtained from Strategy.built_for_mapping / built_for_ordering /
    built_for_overlap; only valid inside that with-block. Reuse skips the
    per-call build a plain Strategy performs, at the price of being pinned
    to exactly one kind of use.

    The part count deliberately stays required at the call site:
    ``graph.partition(64, built)`` cross-checks 64 against the handle rather
    than inferring it. Upstream C also states the part count twice — at
    SCOTCH_stratGraphMapBuild time and at SCOTCH_graphPart time — but
    silently mistunes when the two disagree; here the repetition is hardened
    into an error.
    """

    def __init__(self, strat_data, family: str, nparts: Optional[int]):
        self._strat_data = strat_data
        self._family = family
        self._nparts = nparts
        self._active = True

    def __repr__(self):
        nparts = "" if self._nparts is None else f" nparts={self._nparts}"
        state = "" if self._active else " (expired)"
        return f"<BuiltStrategy {self._family}{nparts}{state}>"

    @property
    @internal_api
    def family(self) -> str:
        """Operation family this strategy was materialized for."""
        return self._family

    @property
    @internal_api
    def nparts(self) -> Optional[int]:
        """Part count this strategy was materialized for (None for ordering)."""
        return self._nparts

    def _check(self, family: str, nparts: Optional[int] = None) -> None:
        if not self._active:
            raise RuntimeError(
                "This materialized strategy has expired: it is only valid "
                "inside the with-block of the built_for_* call that created it."
            )
        if family != self._family:
            raise RuntimeError(
                f"This strategy was materialized for {self._family}; "
                f"it cannot be used for {family}."
            )
        if nparts is not None and int(nparts) != self._nparts:
            raise ValueError(
                f"This strategy was materialized for nparts={self._nparts}; "
                f"it cannot be used with {nparts} parts."
            )

    @contextmanager
    def _materialized_mapping(self, nparts: int):
        self._check("mapping", nparts)
        yield self._strat_data

    @contextmanager
    def _materialized_ordering(self):
        self._check("ordering")
        yield self._strat_data

    @contextmanager
    def _materialized_overlap(self, nparts: int):
        self._check("overlap", nparts)
        yield self._strat_data

    @property
    def _strat(self):
        """Materialized handles are for sequential graph operations only."""
        raise RuntimeError(
            f"A materialized (built_for_*) strategy is specific to sequential "
            f"{self._family}; this operation cannot consume it. Pass a plain "
            "Strategy instead."
        )


class Strategies:
    """
    Collection of common strategy configurations.

    This class provides convenient presets for partitioning and ordering
    strategies. Most users should use `partition_quality()` / `partition_fast()`
    and `order_quality()` / `order_fast()`, which build real Scotch strategies
    from characteristic flags via SCOTCH_stratGraphMapBuild /
    SCOTCH_stratGraphOrderBuild.

    Strategy string notes:
        - "" (or None): Scotch's adaptive default strategy
        - "s": Simple (natural-order) ordering
        - Complex strings: see Scotch's user documentation for the grammar

        Warning:
            Any strategy-valued parameter left implicit defaults to a
            do-nothing dummy (stratdummy in Scotch's method tables) — and
            "complex-looking" is no protection. Bare codes ("r", "m" for
            mapping; "n", "c" for ordering) are the extreme case, but e.g.
            "r{job=t,map=t,poli=S,bal=0.05}" — four parameters, yet missing
            sep= — also silently puts every vertex into a single part, while
            "r{sep=gf}" works. The string parses and the call succeeds either
            way, so PyScotch cannot detect incompleteness for you. When
            hand-writing strategy strings, verify the output (all parts used;
            permutation differs from the identity) — or prefer the flag-based
            API (request_mapping, set_recursive_bisection, ...), whose
            strategies are complete by construction.

    Custom Strategy Examples:
        >>> strategy = Strategy()
        >>> # Use Scotch's built-in defaults (recommended)
        >>> partitions = graph.partition(4, strategy)

        >>> # Flag-based request (built with the right nparts at use time)
        >>> strategy = Strategy()
        >>> strategy.request_mapping(StrategyFlags.QUALITY)
        >>> partitions = graph.partition(4, strategy)

        >>> # Or specify a full custom strategy string
        >>> strategy = Strategy()
        >>> strategy.set_mapping("m{vert=100,low=r{sep=gf},asc=f}")
        >>> partitions = graph.partition(4, strategy)

    Note:
        Complex strategy strings follow Scotch's internal syntax. See:
        - external/scotch/src/libscotch/library_graph_map.c (SCOTCH_stratGraphMapBuild)
        - external/scotch/doc/scotch_user*.pdf for strategy documentation
        - Scotch source code for tested examples
    """

    # Partitioning strategies.
    # "" is safe in PyScotch: set_mapping("") selects the default strategy.
    DEFAULT_PARTITION = ""
    # Bare Scotch method codes, kept for reference; incomplete on their own
    # (see the class docstring) — prefer the flag-based methods.
    RECURSIVE_BISECTION = "r"
    MULTILEVEL = "m"
    # Characteristic flags handed to SCOTCH_stratGraphMapBuild.
    QUALITY_PARTITION = StrategyFlags.QUALITY
    FAST_PARTITION = StrategyFlags.SPEED

    # Ordering strategies
    DEFAULT_ORDER = ""
    NESTED_DISSECTION = "n"
    SIMPLE_ORDER = "s"
    MINIMUM_FILL = "c"
    # Characteristic flags handed to SCOTCH_stratGraphOrderBuild.
    QUALITY_ORDER = StrategyFlags.QUALITY
    FAST_ORDER = StrategyFlags.SPEED

    @staticmethod
    @highlevel_api(scotch_functions=["SCOTCH_stratInit", "SCOTCH_stratGraphMapBuild"])
    def partition_quality() -> Strategy:
        """
        Get a high-quality partitioning strategy.

        Returns a strategy built with SCOTCH_stratGraphMapBuild and the
        QUALITY characteristic flag: quality is privileged over speed.
        """
        strat = Strategy()
        strat.request_mapping(Strategies.QUALITY_PARTITION)
        return strat

    @staticmethod
    @highlevel_api(scotch_functions=["SCOTCH_stratInit", "SCOTCH_stratGraphMapBuild"])
    def partition_fast() -> Strategy:
        """
        Get a fast partitioning strategy.

        Returns a strategy built with SCOTCH_stratGraphMapBuild and the
        SPEED characteristic flag: speed is privileged over quality.
        """
        strat = Strategy()
        strat.request_mapping(Strategies.FAST_PARTITION)
        return strat

    @staticmethod
    @highlevel_api(scotch_functions=["SCOTCH_stratInit", "SCOTCH_stratGraphOrderBuild"])
    def order_quality() -> Strategy:
        """
        Get a high-quality ordering strategy.

        Returns a strategy built with SCOTCH_stratGraphOrderBuild and the
        QUALITY characteristic flag (this matches Scotch's own default
        ordering strategy, which is built with QUALITY).
        """
        strat = Strategy()
        strat.request_ordering(Strategies.QUALITY_ORDER)
        return strat

    @staticmethod
    @highlevel_api(scotch_functions=["SCOTCH_stratInit", "SCOTCH_stratGraphOrderBuild"])
    def order_fast() -> Strategy:
        """
        Get a fast ordering strategy.

        Returns a strategy built with SCOTCH_stratGraphOrderBuild and the
        SPEED characteristic flag: speed is privileged over quality.
        """
        strat = Strategy()
        strat.request_ordering(Strategies.FAST_ORDER)
        return strat
