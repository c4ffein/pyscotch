"""Behavioural regression tests for the default strategies.

These cover a bug where the default-strategy paths went through
SCOTCH_stratGraphMap("") / SCOTCH_stratGraphOrder(""). An empty strategy
string is NOT "use the default" at the C level: it installs an empty method
that does nothing, so partitioning left every vertex unassigned (-1) and
ordering returned the identity permutation. A freshly SCOTCH_stratInit'd
strategy *is* the default.

The methods that originally carried the bug (set_mapping_default /
set_ordering_default) were later removed as redundant family-named aliases
of reset(); the surviving default spellings guarded here are reset(), the
None synonym in the string setters, and a plain Strategy(). "" is NOT a
default spelling: strings are passed to Scotch verbatim, and "" is Scotch's
do-nothing strategy (covered in test_strategy_requests.py).

The pre-existing tests only asserted `strategy.strategy_string == ""`, which
stayed true while the strategy was useless — hence these assert on behaviour.
"""

import numpy as np
import pytest

from pyscotch import Graph, random_reset
from pyscotch.strategy import Strategies, Strategy


def _ring(nvert=12):
    """A simple ring graph: every vertex has exactly two neighbours."""
    verttab = np.arange(0, 2 * nvert + 1, 2)
    edgetab = np.empty(2 * nvert, dtype=np.int64)
    for v in range(nvert):
        edgetab[2 * v] = (v - 1) % nvert
        edgetab[2 * v + 1] = (v + 1) % nvert
    g = Graph()
    g.build(verttab.astype(np.int64), edgetab)
    return g, nvert


class TestDefaultMappingStrategy:
    def test_default_strategy_assigns_every_vertex(self):
        """The default mapping strategy must map all vertices, not leave -1."""
        g, nvert = _ring()
        strat = Strategy()
        strat.reset()
        part = g.partition(2, strat)
        assert (part >= 0).all(), f"unassigned vertices (-1) in partition: {part.tolist()}"
        assert set(part.tolist()) == {0, 1}

    def test_default_strategy_matches_no_strategy(self):
        """Passing the explicit default must behave like passing no strategy."""
        g1, _ = _ring()
        g2, _ = _ring()
        strat = Strategy()
        strat.set_mapping(None)  # None is the string-setter synonym for default
        explicit = g1.partition(2, strat)
        implicit = g2.partition(2)
        assert (explicit >= 0).all() and (implicit >= 0).all()
        # Both must be real 2-way partitions of the ring.
        assert set(explicit.tolist()) == set(implicit.tolist()) == {0, 1}

    def test_default_strategy_keeps_string_bookkeeping(self):
        """Bookkeeping: set_mapping(None) and reset() both read back as
        untouched (None); a verbatim string round-trips."""
        strat = Strategy()
        strat.set_mapping(None)
        assert strat.strategy_string is None
        strat.set_mapping("r{sep=gf}")
        assert strat.strategy_string == "r{sep=gf}"
        strat.reset()
        assert strat.strategy_string is None


class TestDefaultOrderingStrategy:
    def test_default_ordering_is_a_valid_permutation(self):
        g, nvert = _ring()
        permtab, peritab = g.order()
        assert np.array_equal(np.sort(permtab), np.arange(nvert))
        assert np.array_equal(peritab[permtab], np.arange(nvert))

    def test_default_ordering_actually_reorders(self):
        """A do-nothing ordering strategy returns the identity; the default must not.

        A ring is symmetric enough that Scotch's default (nested-dissection based)
        ordering never leaves it untouched — an identity result means the strategy
        did nothing at all.
        """
        g, nvert = _ring(64)
        permtab, _ = g.order()
        assert not np.array_equal(permtab, np.arange(nvert)), (
            "order() returned the identity permutation: the default ordering "
            "strategy performed no reordering at all"
        )

    def test_explicit_default_matches_implicit(self):
        # order() is a thin binding and does NOT reset Scotch's PRNG; comparing
        # two calls for equality requires resetting the state before each.
        g1, _ = _ring(64)
        g2, _ = _ring(64)
        strat = Strategy()
        strat.set_ordering(None)  # None is the string-setter synonym for default
        random_reset()
        perm_explicit, _ = g1.order(strat)
        random_reset()
        perm_implicit, _ = g2.order()
        assert np.array_equal(perm_explicit, perm_implicit)


class TestStrategyReset:
    def test_reset_restores_default_behaviour(self):
        """A configured strategy is recoverable to the default via reset()."""
        strat = Strategy()
        strat.set_mapping("r{sep=gf}")  # a real, explicitly built strategy
        strat.reset()
        g, _ = _ring()
        part = g.partition(2, strat)
        assert (part >= 0).all(), "reset() did not restore a working default strategy"

    def test_reset_clears_recorded_string(self):
        strat = Strategy()
        strat.set_mapping("r")
        strat.reset()
        assert strat.strategy_string is None


@pytest.mark.parametrize("nparts", [2, 3, 4])
def test_cli_default_path_partitions(nparts):
    """The exact strategy path `pyscotch partition` uses must produce a real
    partition (this is what regressed: the CLI default emitted all -1). The
    CLI's default branch is now a plain Strategy() — mirror it exactly."""
    g, _ = _ring(32)
    strat = Strategy()
    part = g.partition(nparts, strat)
    assert (part >= 0).all()
    assert len(set(part.tolist())) == nparts


# ---------------------------------------------------------------------------
# Every strategy PyScotch advertises must actually work.
#
# set_recursive_bisection used to pass the bare Scotch method code "r" — an
# incomplete strategy that put every vertex in one part. It now goes through
# SCOTCH_stratGraphMapBuild via Strategy.request_mapping. (set_multilevel and
# set_nested_dissection, which had the same bug, were removed outright: the
# only honest implementation was an alias of the default build.)
# ---------------------------------------------------------------------------
def _with(method_name):
    """Build a Strategy and call one of its configuration methods."""

    def make():
        s = Strategy()
        getattr(s, method_name)()
        return s

    return make


STRATEGY_FACTORIES = [
    ("reset", _with("reset")),
    ("partition_quality", Strategies.partition_quality),
    ("partition_fast", Strategies.partition_fast),
    ("set_recursive_bisection", _with("set_recursive_bisection")),
]


@pytest.mark.parametrize("case", STRATEGY_FACTORIES, ids=lambda c: c[0])
def test_every_strategy_produces_a_real_partition(case):
    """A strategy that PyScotch exposes must map every vertex into a real part.

    Asserting `part.max() < nparts` alone is what let a total failure ship: an
    all -1 result satisfies it. Assert the lower bound and the balance too.
    """
    _name, make = case
    g, nvert = _ring(32)
    part = g.partition(4, make())
    assert (part >= 0).all(), f"{_name}: left vertices unassigned (-1): {part.tolist()}"
    assert part.max() < 4, f"{_name}: part index out of range"
    assert set(part.tolist()) == {0, 1, 2, 3}, f"{_name}: not all parts used: {part.tolist()}"
    counts = np.bincount(part, minlength=4)
    assert counts.max() <= nvert // 2, (
        f"{_name}: degenerate partition {counts.tolist()} — one part holds "
        "most of the graph, the strategy did no real work"
    )


def test_quality_and_fast_are_distinct_strategies():
    """`quality` and `fast` must not secretly be the same thing as `default`."""
    assert (
        Strategies.QUALITY_PARTITION is not None and Strategies.FAST_PARTITION is not None
    ), "quality/fast are unset, so both silently degrade to the default strategy"
