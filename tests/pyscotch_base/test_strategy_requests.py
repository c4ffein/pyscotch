"""Multi-step behavioural tests for deferred (flag-built) strategies.

Strategy.request_mapping / request_ordering record a SCOTCH_strat*Build request
that is only built by the operation consuming the strategy (Graph.partition
needs nparts, unknown at Strategy creation time). These tests exercise the
life-cycle paths a single-shot test cannot see: reuse across different part
counts, intent overriding, cross-operation misuse, and the guard that keeps an
unbuilt request from silently degrading to the default strategy.
"""

import re
from pathlib import Path

import numpy as np
import pytest

import pyscotch
from pyscotch import Graph, Mesh, StrategyFlags, random_reset
from pyscotch import libscotch as lib
from pyscotch import strategy as strategy_module
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


def _grid(side=20):
    """A side x side grid graph — big enough (>240 vertices for side=20) that
    nested dissection actually splits it, so every ordering flag must produce
    a non-identity permutation (below Scotch's vert>240 threshold the whole
    graph is a single leaf and e.g. LEAF_SIMPLE legitimately returns the
    natural order)."""
    nvert = side * side
    verttab = [0]
    edgetab = []
    for v in range(nvert):
        neighbours = []
        if v >= side:
            neighbours.append(v - side)
        if v < nvert - side:
            neighbours.append(v + side)
        if v % side:
            neighbours.append(v - 1)
        if v % side != side - 1:
            neighbours.append(v + 1)
        edgetab.extend(neighbours)
        verttab.append(len(edgetab))
    g = Graph()
    g.build(np.array(verttab, dtype=np.int64), np.array(edgetab, dtype=np.int64))
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
            # PyScotch never resets implicitly (upstream semantics: the PRNG
            # stream carries across calls); comparing repeated calls for
            # equality requires resetting the stream ourselves each time.
            random_reset()
            part = g.partition(4, strat)
            _assert_real_partition(part, 4, nvert)
            results.append(part)
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


class TestUpstreamContractPins:
    """Guards for the places where a silent regression could hide: constants
    copied from Scotch's sources, the guard-bypass invariant, and the deferred
    build cache. Each of these was once verified by hand; these tests make the
    verification permanent."""

    LIBSCOTCH_SRC = (
        Path(__file__).resolve().parents[2] / "external" / "scotch" / "src" / "libscotch"
    )
    LIBRARY_H = LIBSCOTCH_SRC / "library.h"

    def test_strategy_flags_match_library_h(self):
        """StrategyFlags hardcodes SCOTCH_STRAT* values; if one drifted from
        library.h, request_mapping(QUALITY) would silently build a different
        strategy. Compare every named member against the checkout's header."""
        if not self.LIBRARY_H.exists():
            pytest.skip("scotch submodule not initialized")
        c_values = {
            name: int(value, 16)
            for name, value in re.findall(
                r"#define\s+SCOTCH_STRAT(\w+)\s+0x([0-9A-Fa-f]+)",
                self.LIBRARY_H.read_text(),
            )
        }
        py_values = {
            name.replace("_", ""): member.value
            for name, member in StrategyFlags.__members__.items()
        }
        assert py_values == c_values

    def test_no_code_bypasses_the_strat_guard(self):
        """Only strategy.py may touch _strat_data. Every other module must go
        through the guarded _strat property; a direct access would let an
        operation silently run the default strategy while a request is
        pending — the do-nothing-strategy bug class all over again."""
        package_dir = Path(pyscotch.__file__).parent
        offenders = sorted(
            path.name
            for path in package_dir.rglob("*.py")
            if path.name != "strategy.py" and "_strat_data" in path.read_text()
        )
        assert offenders == []

    def test_default_balance_constants_match_upstream_sources(self):
        """_DEFAULT_MAPPING_BALANCE / _DEFAULT_ORDERING_BALANCE are copied
        from the default-strategy builds in the C sources. Behavioural
        equivalence on small deterministic graphs cannot detect a small drift
        (verified: balance 0.01 vs 0.05 partitions a 24-ring identically, and
        graphs big enough to discriminate are threading-nondeterministic), so
        pin the constants against the source text directly."""
        map_c = self.LIBSCOTCH_SRC / "library_graph_map.c"
        order_c = self.LIBSCOTCH_SRC / "library_graph_order.c"
        if not map_c.exists():
            pytest.skip("scotch submodule not initialized")

        map_builds = re.findall(
            r"SCOTCH_stratGraphMapBuild\s*\(straptr,\s*SCOTCH_STRATDEFAULT,.*?,\s*([\d.]+)\)",
            map_c.read_text(),
        )
        assert map_builds, "default mapping build not found in library_graph_map.c"
        assert {float(b) for b in map_builds} == {
            strategy_module._DEFAULT_MAPPING_BALANCE
        }

        order_builds = re.findall(
            r"SCOTCH_stratGraphOrderBuild\s*\(straptr,\s*SCOTCH_STRAT(\w+),\s*(\d+),\s*([\d.]+)\)",
            order_c.read_text(),
        )
        assert order_builds, "default ordering build not found in library_graph_order.c"
        for flag_name, levels, balance in order_builds:
            # order_quality() == "Scotch's own default" rests on QUALITY here.
            assert flag_name == "QUALITY"
            assert int(levels) == 0
            assert float(balance) == strategy_module._DEFAULT_ORDERING_BALANCE

        # Overlap partitioning has its OWN default balance (0.05, not the
        # mapping family's 0.01) — the deviation that motivated balance=None.
        ovl_c = self.LIBSCOTCH_SRC / "library_graph_part_ovl.c"
        ovl_builds = re.findall(
            r"SCOTCH_stratGraphPartOvlBuild\s*\(straptr,\s*SCOTCH_STRAT(\w+),"
            r"\s*\(Gnum\)\s*partnbr,\s*\(double\)\s*([\d.]+)\)",
            ovl_c.read_text(),
        )
        assert ovl_builds, "default overlap build not found in library_graph_part_ovl.c"
        for _flag_name, balance in ovl_builds:
            assert float(balance) == strategy_module._DEFAULT_OVERLAP_BALANCE

    def test_balance_none_resolves_per_consuming_operation(self, monkeypatch):
        """balance=None must resolve to the CONSUMING operation's upstream
        default: 0.01 for a mapping build, 0.05 for an overlap build. Small
        graphs cannot discriminate behaviourally (verified: 0.01 vs 0.05
        partition a small ring identically), so capture the balance actually
        handed to libscotch at the ctypes boundary. An explicit balance must
        pass through untouched for every consumer."""
        recorded = {}
        real_map = lib.SCOTCH_stratGraphMapBuild
        real_ovl = lib.SCOTCH_stratGraphPartOvlBuild

        def spy_map(strat, flags, nparts, balance):
            recorded["map"] = balance
            return real_map(strat, flags, nparts, balance)

        def spy_ovl(strat, flags, nparts, balance):
            recorded["ovl"] = balance
            return real_ovl(strat, flags, nparts, balance)

        monkeypatch.setattr(lib, "SCOTCH_stratGraphMapBuild", spy_map)
        monkeypatch.setattr(lib, "SCOTCH_stratGraphPartOvlBuild", spy_ovl)

        g, _ = _ring(24)
        strat = Strategy()
        strat.request_mapping()
        g.partition(4, strat)
        assert recorded["map"] == strategy_module._DEFAULT_MAPPING_BALANCE

        g, _ = _ring(24)
        strat = Strategy()
        strat.request_mapping()
        g.partition_overlap(4, strat)
        assert recorded["ovl"] == strategy_module._DEFAULT_OVERLAP_BALANCE

        g, _ = _ring(24)
        strat = Strategy()
        strat.request_mapping(balance=0.03)
        g.partition_overlap(4, strat)
        assert recorded["ovl"] == 0.03

    def test_flag_built_default_partition_matches_implicit_default(self):
        """request_mapping(DEFAULT) must build the exact strategy Scotch
        builds itself for an untouched Strat (library_graph_map.c:
        STRATDEFAULT, nparts, 0.01). From identical PRNG state the partitions
        must be identical — this catches flag-wiring drift (a 24-ring
        partitions differently under QUALITY, empirically verified). Balance
        drift is caught by the source-text pin above, not here."""
        results = []
        explicit = Strategy()
        explicit.request_mapping(StrategyFlags.DEFAULT)
        for strat in (Strategy(), explicit):
            g, nvert = _ring(24)
            random_reset()
            part = g.partition(4, strat)
            _assert_real_partition(part, 4, nvert)
            results.append(part)
        assert np.array_equal(results[0], results[1])

    def test_flag_built_quality_ordering_matches_implicit_default(self):
        """Scotch's implicit default ordering IS OrderBuild(QUALITY, 0, 0.2)
        (library_graph_order.c), so request_ordering(QUALITY) must reproduce
        it exactly from identical PRNG state. This catches build-path wiring
        (a lost or garbage request would diverge from the default); it cannot
        catch fine flag/balance drift — a 64-ring orders identically under
        QUALITY, SPEED, and any balance (empirically verified), and bigger
        graphs are threading-nondeterministic. The header and source-text
        pins above cover constant drift."""
        results = []
        explicit = Strategy()
        explicit.request_ordering(StrategyFlags.QUALITY)
        for strat in (Strategy(), explicit):
            g, nvert = _ring(64)
            random_reset()
            perm, _ = g.order(strat)
            assert np.array_equal(np.sort(perm), np.arange(nvert))
            results.append(perm)
        assert np.array_equal(results[0], results[1])

    def test_request_alternating_operations_rebuilds_per_grammar(self):
        """Each consuming operation builds the request in its OWN grammar: the
        same flag request used for partition, then partition_overlap, then
        partition again must yield a valid result each time. Sharing one built
        strategy across operations would hand the overlap op a plain mapping
        strategy (or vice versa)."""
        strat = Strategy()
        strat.request_mapping(StrategyFlags.QUALITY)
        g, nvert = _ring(32)

        part = g.partition(4, strat)
        _assert_real_partition(part, 4, nvert)

        overlap = g.partition_overlap(4, strat)
        assert set(overlap.tolist()) <= {-1, 0, 1, 2, 3}
        assert set(overlap.tolist()) >= {0, 1, 2, 3}, "not all parts present"

        part2 = g.partition(4, strat)
        _assert_real_partition(part2, 4, nvert)


class TestEveryFlagBehaves:
    """Every StrategyFlags characteristic must build a working strategy.

    SCOTCH_strat*Build accepts any flag combination without complaint; the
    only way to know a flag is wired up is to check the output. These sweeps
    guard the whole flag surface, not just the QUALITY/SPEED/RECURSIVE subset
    the presets use."""

    MAPPING_FLAGS = [
        StrategyFlags.DEFAULT,
        StrategyFlags.QUALITY,
        StrategyFlags.SPEED,
        StrategyFlags.BALANCE,
        StrategyFlags.SAFETY,
        StrategyFlags.SCALABILITY,
        StrategyFlags.RECURSIVE,
        StrategyFlags.REMAP,
        StrategyFlags.DISCONNECTED,
        StrategyFlags.QUALITY | StrategyFlags.SAFETY,  # the docstring example
    ]

    ORDERING_FLAGS = [
        StrategyFlags.DEFAULT,
        StrategyFlags.QUALITY,
        StrategyFlags.SPEED,
        StrategyFlags.BALANCE,
        StrategyFlags.SAFETY,
        StrategyFlags.SCALABILITY,
        StrategyFlags.LEAF_SIMPLE,
        StrategyFlags.SEPA_SIMPLE,
        StrategyFlags.DISCONNECTED,
        StrategyFlags.QUALITY | StrategyFlags.SPEED,
    ]

    @pytest.mark.parametrize("flags", MAPPING_FLAGS, ids=str)
    def test_mapping_flag_produces_real_partition(self, flags):
        g, nvert = _grid(20)
        strat = Strategy()
        strat.request_mapping(flags)
        part = g.partition(4, strat)
        _assert_real_partition(part, 4, nvert)

    @pytest.mark.parametrize("flags", ORDERING_FLAGS, ids=str)
    def test_ordering_flag_produces_real_ordering(self, flags):
        g, nvert = _grid(20)
        strat = Strategy()
        strat.request_ordering(flags)
        perm, peri = g.order(strat)
        assert np.array_equal(np.sort(perm), np.arange(nvert))
        assert np.array_equal(peri[perm], np.arange(nvert))
        assert not np.array_equal(perm, np.arange(nvert)), (
            f"flags={flags!r} performed no reordering at all"
        )

    @pytest.mark.parametrize(
        "flags", [StrategyFlags.LEVEL_MAX, StrategyFlags.LEVEL_MIN], ids=str
    )
    def test_ordering_level_flags_with_levels(self, flags):
        """LEVEL_MAX/LEVEL_MIN are only meaningful with a levels bound."""
        g, nvert = _grid(20)
        strat = Strategy()
        strat.request_ordering(flags, levels=3)
        perm, _ = g.order(strat)
        assert np.array_equal(np.sort(perm), np.arange(nvert))
        assert not np.array_equal(perm, np.arange(nvert))

    def test_order_fast_preset(self):
        """Strategies.order_fast() was never exercised anywhere."""
        g, nvert = _grid(20)
        perm, peri = g.order(Strategies.order_fast())
        assert np.array_equal(np.sort(perm), np.arange(nvert))
        assert np.array_equal(peri[perm], np.arange(nvert))
        assert not np.array_equal(perm, np.arange(nvert))

    def test_set_overlap_partitioning_empty_is_default(self):
        """The "" -> reset-to-default branch of the overlap string setter."""
        g, nvert = _ring(32)
        strat = Strategy()
        strat.set_overlap_partitioning("")
        part = g.partition_overlap(4, strat)
        assert len(part) == nvert
        assert set(part.tolist()) <= {-1, 0, 1, 2, 3}
        assert set(part.tolist()) >= {0, 1, 2, 3}, "not all parts present"


class TestFailedStringStaysFailed:
    """A constructor string that fails to parse must fail on EVERY use.

    The deferred build hands the string to the target operation at use time;
    if the failed attempt dropped the pending string, the next call with the
    same Strategy would silently run the default strategy — the quieter
    sibling of the do-nothing-strategy bug."""

    def test_failed_mapping_string_fails_again_on_retry(self):
        g, _ = _ring(20)
        strat = Strategy("this-is-not-a-strategy")
        with pytest.raises(RuntimeError, match="Failed to set mapping strategy"):
            g.partition(2, strat)
        g2, _ = _ring(20)
        with pytest.raises(RuntimeError, match="Failed to set mapping strategy"):
            g2.partition(2, strat)

    def test_failed_ordering_string_fails_again_on_retry(self):
        g, _ = _ring(20)
        strat = Strategy("this-is-not-a-strategy")
        with pytest.raises(RuntimeError, match="Failed to set ordering strategy"):
            g.order(strat)
        with pytest.raises(RuntimeError, match="Failed to set ordering strategy"):
            g.order(strat)

    def test_failed_overlap_string_fails_again_on_retry(self):
        g, _ = _ring(20)
        strat = Strategy("this-is-not-a-strategy")
        with pytest.raises(RuntimeError, match="Failed to set overlap partitioning strategy"):
            g.partition_overlap(2, strat)
        with pytest.raises(RuntimeError, match="Failed to set overlap partitioning strategy"):
            g.partition_overlap(2, strat)


class TestStrategyIsImmutableSpec:
    """Clone-per-call semantics: a Strategy is a specification; consuming it
    builds a private per-call strat and never mutates the Strategy. These pin
    the three guarantees that fall out: thread-shareability (the first
    scenario segfaulted under the earlier rebuild-in-place design), the
    optional C-style nparts pin, and default strategies crossing operation
    families."""

    def test_shared_strategy_across_threads_with_different_nparts(self):
        """Two threads, ONE Strategy, different part counts. Under the old
        rebuild-in-place design this segfaulted (one thread freed the strategy
        AST the other was executing — ctypes releases the GIL during C calls);
        with per-call builds there is no shared mutable strategy state left."""
        import threading

        strat = Strategy()
        strat.request_mapping(StrategyFlags.QUALITY)
        errors = []
        barrier = threading.Barrier(2)

        def worker(nparts):
            try:
                g, nvert = _ring(256)
                barrier.wait()
                for _ in range(25):
                    part = g.partition(nparts, strat)
                    _assert_real_partition(part, nparts, nvert)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in (4, 7)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []

    def test_nparts_pin_matches_c_contract(self):
        """request_mapping(nparts=...) pins the part count like the C API
        (SCOTCH_stratGraphMapBuild fixes partnbr at build time) — but loudly:
        a mismatching call raises instead of silently running a mistuned
        strategy."""
        g, nvert = _ring(24)
        strat = Strategy()
        strat.request_mapping(StrategyFlags.QUALITY, nparts=4)
        part = g.partition(4, strat)
        _assert_real_partition(part, 4, nvert)
        with pytest.raises(ValueError, match="nparts=4"):
            g.partition(8, strat)
        with pytest.raises(ValueError, match="nparts=4"):
            g.partition_overlap(8, strat)

    def test_default_strategy_crosses_operation_families(self):
        """A never-configured Strategy materializes as a private EMPTY strat
        per call, so Scotch's implicit-default build cannot cache itself into
        the shared object. Consequence: the same default Strategy works for
        partition then order. (The equivalent raw C sequence fails with 'not
        a sequential graph ordering strategy': SCOTCH_graphPart deposits a
        mapping strategy into the caller's SCOTCH_Strat.)"""
        strat = Strategy()
        g, nvert = _ring(64)
        part = g.partition(4, strat)
        _assert_real_partition(part, 4, nvert)
        perm, peri = g.order(strat)
        assert np.array_equal(np.sort(perm), np.arange(nvert))
        assert np.array_equal(peri[perm], np.arange(nvert))
        part2 = g.partition(4, strat)
        _assert_real_partition(part2, 4, nvert)

    def test_use_does_not_mutate_strategy_string(self):
        """Consuming a constructor string leaves the Strategy untouched."""
        strat = Strategy("r{sep=gf}")
        g, nvert = _ring(24)
        part = g.partition(4, strat)
        _assert_real_partition(part, 4, nvert)
        assert strat.strategy_string == "r{sep=gf}"


class TestBuiltStrategyHandles:
    """The materialized tier: Strategy.built_for_* yields a BuiltStrategy
    handle compiled once for one operation family (and part count), valid
    inside its with-block. The part count stays explicit at every call site
    and is cross-checked against the handle: upstream C also states nparts
    twice (SCOTCH_stratGraphMapBuild and SCOTCH_graphPart) but silently
    mistunes when they disagree — here the repetition is hardened into an
    error."""

    def test_built_mapping_matches_naive_path_exactly(self):
        """Materialized reuse must be bit-identical to per-call builds from
        the same PRNG state — the handle skips the rebuild, never changes
        what is built."""
        strat = Strategy()
        strat.request_mapping(StrategyFlags.QUALITY)
        naive = []
        for _ in range(3):
            g, nvert = _ring(32)
            random_reset()
            part = g.partition(4, strat)
            _assert_real_partition(part, 4, nvert)
            naive.append(part)
        with strat.built_for_mapping(4) as built:
            for i in range(3):
                g, nvert = _ring(32)
                random_reset()
                part = g.partition(4, built)
                assert np.array_equal(part, naive[i])

    def test_built_nparts_mismatch_raises(self):
        strat = Strategy()
        strat.request_mapping()
        g, _ = _ring(24)
        with strat.built_for_mapping(4) as built:
            with pytest.raises(ValueError, match="nparts=4"):
                g.partition(8, built)
        with strat.built_for_overlap(4) as built:
            with pytest.raises(ValueError, match="nparts=4"):
                g.partition_overlap(8, built)

    def test_built_family_mismatch_raises(self):
        strat = Strategy()
        strat.request_mapping()
        g, _ = _ring(24)
        with strat.built_for_mapping(4) as built:
            with pytest.raises(RuntimeError, match="mapping"):
                g.order(built)
            with pytest.raises(RuntimeError, match="mapping"):
                g.partition_overlap(4, built)  # overlap is its own grammar

    def test_built_ordering_works_and_rejects_partition(self):
        strat = Strategy()
        strat.request_ordering(StrategyFlags.QUALITY)
        with strat.built_for_ordering() as built:
            g, nvert = _grid(20)
            perm, peri = g.order(built)
            assert np.array_equal(np.sort(perm), np.arange(nvert))
            assert np.array_equal(peri[perm], np.arange(nvert))
            assert not np.array_equal(perm, np.arange(nvert))
            with pytest.raises(RuntimeError, match="ordering"):
                g.partition(4, built)

    def test_built_overlap_works(self):
        strat = Strategy()
        strat.request_mapping()
        with strat.built_for_overlap(4) as built:
            g, nvert = _ring(32)
            part = g.partition_overlap(4, built)
            assert set(part.tolist()) <= {-1, 0, 1, 2, 3}
            assert set(part.tolist()) >= {0, 1, 2, 3}, "not all parts present"

    def test_built_handle_expires_with_its_block(self):
        strat = Strategy()
        strat.request_mapping()
        with strat.built_for_mapping(4) as built:
            pass
        g, _ = _ring(24)
        with pytest.raises(RuntimeError, match="expired"):
            g.partition(4, built)

    def test_built_respects_request_pin(self):
        """A request pinned to nparts=4 refuses to materialize for 8 — the
        pin check happens at build time, before any operation runs."""
        strat = Strategy()
        strat.request_mapping(nparts=4)
        with pytest.raises(ValueError, match="nparts=4"):
            with strat.built_for_mapping(8):
                pass

    def test_built_from_constructor_string(self):
        strat = Strategy("r{sep=gf}")
        with strat.built_for_mapping(4) as built:
            g, nvert = _ring(24)
            part = g.partition(4, built)
            assert set(part.tolist()) == {0, 1, 2, 3}

    def test_built_default_strategy_loops_and_spec_survives(self):
        """A default Strategy materialized for mapping: Scotch's implicit
        build lands in the handle's private strat on first use and is safely
        reused — the nparts cross-check is what makes that reuse correct.
        The spec Strategy itself stays untouched and usable afterwards."""
        strat = Strategy()
        with strat.built_for_mapping(4) as built:
            for _ in range(3):
                g, nvert = _ring(32)
                part = g.partition(4, built)
                _assert_real_partition(part, 4, nvert)
        g, nvert = _ring(32)
        part = g.partition(5, strat)
        _assert_real_partition(part, 5, nvert)


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
        """WARNING: this test pins UNDESIRED upstream behaviour (the stratdummy
        trap). It MUST eventually FAIL — the day a Scotch release fixes
        implicit sub-strategies — and MUST then be DELETED, unskipping
        test_future_incomplete_strategies_no_longer_silent below instead."""
        g, nvert = _ring(24)
        strat = Strategy()
        strat.set_mapping(Strategies.MULTILEVEL)
        part = g.partition(4, strat)
        assert len(set(part.tolist())) == 1, (
            "bare 'm' stopped being degenerate — if Scotch fixed this, "
            "revisit the set_multilevel() docstring and QUESTIONS_FOR_SCOTCH_TEAM.md"
        )

    def test_incomplete_complex_string_is_degenerate_but_complete_works(self):
        """The stratdummy trap is not limited to bare codes: a parameterized
        string that omits a strategy-valued parameter (here sep=) is equally
        degenerate, while its spelled-out sibling works. Pins the exact pair
        the Strategies docstring warns about.

        WARNING: the degenerate half of this test pins UNDESIRED upstream
        behaviour. It MUST eventually FAIL — the day a Scotch release fixes
        implicit sub-strategies — and MUST then be DELETED, unskipping
        test_future_incomplete_strategies_no_longer_silent below instead.
        (The r{sep=gf} half must keep passing forever.)"""
        g, nvert = _ring(24)
        strat = Strategy()
        strat.set_mapping("r{job=t,map=t,poli=S,bal=0.05}")   # complex-looking, no sep=
        part = g.partition(4, strat)
        assert len(set(part.tolist())) == 1, (
            "incomplete complex string stopped being degenerate — if Scotch "
            "fixed implicit sub-strategies, revisit the Strategies docstring "
            "warning and QUESTIONS_FOR_SCOTCH_TEAM.md"
        )

        g2, _ = _ring(24)
        strat2 = Strategy()
        strat2.set_mapping("r{sep=gf}")                       # sub-strategy spelled out
        part2 = g2.partition(4, strat2)
        assert set(part2.tolist()) == {0, 1, 2, 3}, "complete string must do real work"

    @pytest.mark.skip(
        reason="Parked future contract: unskip (and delete the two pinning tests "
        "above) when upstream fixes stratdummy implicit sub-strategies — see "
        "QUESTIONS_FOR_SCOTCH_TEAM.md. It MUST pass then."
    )
    def test_future_incomplete_strategies_no_longer_silent(self):
        """The desired end state, whichever shape upstream chooses: an
        incomplete strategy string must either be REJECTED (parse/use error)
        or do REAL work — never silently degenerate. Asserts the invariant
        'the trap is gone' rather than betting on one fix."""

        def trap_is_gone_mapping(string):
            g, _ = _ring(24)
            strat = Strategy()
            try:
                strat.set_mapping(string)
                part = g.partition(4, strat)
            except RuntimeError:
                return True                    # rejected loudly: acceptable fix
            return len(set(part.tolist())) > 1  # or it does real work

        def trap_is_gone_ordering(string):
            g, nvert = _ring(64)
            strat = Strategy()
            try:
                strat.set_ordering(string)
                perm, _ = g.order(strat)
            except RuntimeError:
                return True
            return not np.array_equal(perm, np.arange(nvert))

        assert trap_is_gone_mapping("m"), "bare 'm' is still a silent trap"
        assert trap_is_gone_mapping("r{job=t,map=t,poli=S,bal=0.05}"), (
            "incomplete complex string is still a silent trap"
        )
        assert trap_is_gone_ordering("n"), "bare 'n' is still a silent trap"

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
