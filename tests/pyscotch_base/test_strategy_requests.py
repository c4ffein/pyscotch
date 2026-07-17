"""Multi-step behavioural tests for deferred (flag-built) strategies.

Strategy.request_mapping / request_ordering record a SCOTCH_strat*Build request
that is only built by the operation consuming the strategy (Graph.partition
needs nparts, unknown at Strategy creation time). These tests exercise the
life-cycle paths a single-shot test cannot see: reuse across different part
counts, intent overriding, cross-operation misuse, and the guard that keeps an
unbuilt request from silently degrading to the default strategy.
"""

import numpy as np
import pytest

from pyscotch import Graph, Mesh, StrategyFlags
from pyscotch import libscotch as lib
from pyscotch.strategy import Strategies, Strategy


def _ring(nvert=24):
    """A ring graph: every vertex has exactly two neighbours."""
    verttab = np.arange(0, 2 * nvert + 1, 2)
    edgetab = np.empty(2 * nvert, dtype=np.int64)
    for v in range(nvert):
        edgetab[2 * v] = (v - 1) % nvert
        edgetab[2 * v + 1] = (v + 1) % nvert
    g = Graph()
    g.build(verttab.astype(np.int64), edgetab)
    return g, nvert


def _assert_real_partition(part, nparts, nvert):
    assert len(part) == nvert
    assert (part >= 0).all(), f"unassigned vertices (-1): {part.tolist()}"
    assert set(part.tolist()) == set(range(nparts)), f"parts used: {set(part.tolist())}"
    counts = np.bincount(part, minlength=nparts)
    assert counts.max() <= nvert // 2, f"degenerate partition: {counts.tolist()}"


class TestRequestReuse:
    def test_same_strategy_reused_for_different_nparts(self):
        """A flag request is rebuilt when the part count changes.

        Upstream, a strategy built for k parts is tuned to that k; reusing the
        Python-level request must re-run SCOTCH_stratGraphMapBuild per k, not
        keep the first build forever.
        """
        strat = Strategies.partition_quality()
        for nparts in [2, 4, 3, 2]:
            g, nvert = _ring(24)
            part = g.partition(nparts, strat)
            _assert_real_partition(part, nparts, nvert)

    def test_request_survives_many_calls_same_nparts(self):
        """Repeated use with the same nparts stays valid (build is cached)."""
        strat = Strategy()
        strat.request_mapping(StrategyFlags.RECURSIVE)
        results = []
        for _ in range(3):
            g, nvert = _ring(24)
            part = g.partition(4, strat)
            _assert_real_partition(part, 4, nvert)
            results.append(part)
        # reset_random=True (the default) resets Scotch's PRNG per call, so
        # identical calls must give identical partitions — without the reset,
        # carried-over PRNG state shifts part labels or degrades the result.
        assert np.array_equal(results[0], results[1])
        assert np.array_equal(results[1], results[2])

    def test_ordering_request_reused(self):
        strat = Strategies.order_quality()
        for nvert in [24, 64]:
            g, _ = _ring(nvert)
            perm, peri = g.order(strat)
            assert np.array_equal(np.sort(perm), np.arange(nvert))
            assert np.array_equal(peri[perm], np.arange(nvert))


class TestConstructorString:
    def test_constructor_mapping_string_is_applied(self):
        """Strategy("...") must configure the partitioning, not be silently dropped.

        This was a latent bug: the constructor stored the string in its
        bookkeeping and never handed it to Scotch. Note the sub-strategy must
        be spelled out (sep=gf): the string grammar's implicit defaults are
        do-nothing dummies (stratdummy in kgraph_map_st.c).
        """
        g, nvert = _ring(20)
        part = g.partition(4, Strategy("r{sep=gf}"))
        _assert_real_partition(part, 4, nvert)

    def test_constructor_ordering_string_is_applied(self):
        """The same constructor string routes to the ordering grammar for order().

        "s" is the simple method: the natural (identity) order. The default
        strategy reorders this ring (asserted in test_strategy_defaults), so
        an identity result proves the string was applied — a dropped string
        would have produced the default's non-identity permutation.
        """
        g, nvert = _ring(64)
        default_perm, _ = g.order()
        assert not np.array_equal(default_perm, np.arange(nvert)), (
            "precondition: the default must reorder, or this test proves nothing"
        )
        perm, _ = g.order(Strategy("s"))
        assert np.array_equal(perm, np.arange(nvert))

    def test_constructor_string_parse_errors_surface(self):
        """An invalid constructor string must fail loudly at use time, not never."""
        g, _ = _ring(20)
        with pytest.raises(RuntimeError, match="Failed to set mapping strategy"):
            g.partition(4, Strategy("this-is-not-a-strategy"))

    def test_constructor_empty_string_is_default(self):
        g, nvert = _ring(20)
        part = g.partition(2, Strategy(""))
        _assert_real_partition(part, 2, nvert)


class TestEmptyStringIsDefault:
    def test_set_mapping_empty_partitions_everything(self):
        """set_mapping("") means "default", not "do-nothing method".

        At the raw C level SCOTCH_stratGraphMap("") builds an empty method
        that leaves every vertex at -1; PyScotch maps "" to the default
        strategy so the documented DEFAULT_PARTITION = "" constant is safe.
        """
        g, nvert = _ring(20)
        strat = Strategy()
        strat.set_mapping(Strategies.DEFAULT_PARTITION)
        part = g.partition(2, strat)
        _assert_real_partition(part, 2, nvert)

    def test_set_ordering_empty_actually_reorders(self):
        g, nvert = _ring(64)
        strat = Strategy()
        strat.set_ordering(Strategies.DEFAULT_ORDER)
        perm, _ = g.order(strat)
        assert np.array_equal(np.sort(perm), np.arange(nvert))
        assert not np.array_equal(perm, np.arange(nvert)), (
            "set_ordering('') performed no reordering at all"
        )


class TestCrossOperationMisuse:
    def test_ordering_request_rejected_by_partition(self):
        g, _ = _ring(20)
        strat = Strategy()
        strat.request_ordering(StrategyFlags.QUALITY)
        with pytest.raises(RuntimeError, match="cannot be used for partitioning"):
            g.partition(2, strat)

    def test_mapping_request_rejected_by_order(self):
        g, _ = _ring(20)
        strat = Strategy()
        strat.request_mapping(StrategyFlags.QUALITY)
        with pytest.raises(RuntimeError, match="cannot be used for ordering"):
            g.order(strat)

    def test_unbuilt_request_rejected_by_unwired_operation(self):
        """An operation that cannot build a pending request must refuse it.

        Mesh.order does not know how to build graph-strategy requests; using
        the empty underlying strat silently would be the do-nothing-strategy
        bug all over again.
        """
        dtype = lib.get_scotch_dtype()
        verttab = np.array([0, 3, 6, 7, 9, 11, 12], dtype=dtype)
        edgetab = np.array([2, 3, 4, 3, 4, 5, 0, 0, 1, 0, 1, 1], dtype=dtype)
        mesh = Mesh()
        mesh.build(2, 4, verttab, edgetab, velmbas=0, vnodbas=2)
        strat = Strategy()
        strat.request_ordering(StrategyFlags.QUALITY)
        with pytest.raises(RuntimeError, match="does not know how to build"):
            mesh.order(strat)


class TestIntentOverride:
    def test_explicit_string_overrides_request(self):
        """set_mapping after request_mapping wins, and works.

        The string is the multilevel example from the Strategies docstring;
        this keeps the documented example verified.
        """
        g, nvert = _ring(20)
        strat = Strategy()
        strat.request_mapping(StrategyFlags.SPEED)
        strat.set_mapping("m{vert=100,low=r{sep=gf},asc=f}")
        assert strat.strategy_string == "m{vert=100,low=r{sep=gf},asc=f}"
        part = g.partition(4, strat)
        _assert_real_partition(part, 4, nvert)

    def test_reset_clears_request(self):
        """reset() drops a pending request; the strategy is the plain default."""
        strat = Strategy()
        strat.request_ordering(StrategyFlags.QUALITY)
        strat.reset()
        g, nvert = _ring(20)
        # Would raise "cannot be used for partitioning" if the request survived.
        part = g.partition(2, strat)
        _assert_real_partition(part, 2, nvert)

    def test_request_after_string_replaces_it(self):
        g, nvert = _ring(20)
        strat = Strategy()
        strat.set_mapping("m{vert=100}")
        strat.request_mapping(StrategyFlags.RECURSIVE)
        assert strat.strategy_string is None
        part = g.partition(4, strat)
        _assert_real_partition(part, 4, nvert)


class TestOtherPartitioningOperations:
    def test_partition_fixed_honours_request_and_fixed_vertices(self):
        g, nvert = _ring(24)
        fixed = np.full(nvert, -1, dtype=np.int64)
        fixed[0] = 0
        fixed[12] = 1
        strat = Strategies.partition_quality()
        part = g.partition_fixed(2, fixed, strat)
        assert part[0] == 0 and part[12] == 1, "fixed vertices moved"
        _assert_real_partition(part, 2, nvert)

    def test_partition_overlap_honours_request(self):
        """Flag requests build via SCOTCH_stratGraphPartOvlBuild for overlap.

        Overlap partition values: 0..nparts-1 for parts, -1 for vertices in
        the overlap shared between parts.
        """
        g, nvert = _ring(32)
        strat = Strategies.partition_quality()
        part = g.partition_overlap(4, strat)
        assert len(part) == nvert
        assert set(part.tolist()) <= {-1, 0, 1, 2, 3}
        assert set(part.tolist()) >= {0, 1, 2, 3}, "not all parts present"

    def test_repart_honours_request(self):
        g, nvert = _ring(24)
        old = g.partition(2)
        strat = Strategies.partition_fast()
        new = g.repart(2, old, strategy=strat)
        _assert_real_partition(new, 2, nvert)


class TestBrokenBareStringsStayExplicit:
    """Bare method codes remain available through set_* for users who ask for
    them, with their real (degenerate) Scotch semantics — the presets no longer
    use them. These pin the behaviour that motivated the flag-based fix."""

    def test_bare_m_is_still_degenerate(self):
        g, nvert = _ring(24)
        strat = Strategy()
        strat.set_mapping(Strategies.MULTILEVEL)
        part = g.partition(4, strat)
        assert len(set(part.tolist())) == 1, (
            "bare 'm' stopped being degenerate — if Scotch fixed this, "
            "revisit the set_multilevel() docstring and QUESTIONS_FOR_SCOTCH_TEAM.md"
        )

    def test_set_nested_dissection_reorders(self):
        """set_nested_dissection used bare 'n', which returned the identity."""
        g, nvert = _ring(64)
        strat = Strategy()
        strat.set_nested_dissection()
        perm, _ = g.order(strat)
        assert np.array_equal(np.sort(perm), np.arange(nvert))
        assert not np.array_equal(perm, np.arange(nvert)), (
            "set_nested_dissection() performed no reordering at all"
        )
