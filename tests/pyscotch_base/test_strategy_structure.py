"""Structural strategy tests: assert on the BUILT strategy itself, via
SCOTCH_stratSave round-trips, not on operation output.

Outputs can coincide by luck; structures cannot. These tests prove
which-strategy-was-built for every flag preset, and pin two verified
upstream facts (see QUESTIONS_FOR_SCOTCH_TEAM.md): the mapping builder
ignores SCOTCH_STRATSPEED, and the ordering builder ignores
SCOTCH_STRATQUALITY — so one "preset" per family is structurally the default.
If an upstream release changes either, the pins turn red and the docs must be
updated.
"""

from ctypes import byref, c_double

import pytest

from pyscotch import StrategyFlags
from pyscotch import libscotch as lib
from pyscotch.strategy import _ephemeral_strat, _saved_form


def built_mapping(flags, nparts=4, balance=0.01):
    with _ephemeral_strat() as strat:
        ret = lib.SCOTCH_stratGraphMapBuild(
            byref(strat), lib.SCOTCH_Num(int(flags)), lib.SCOTCH_Num(nparts), c_double(balance)
        )
        assert ret == 0
        return _saved_form(strat)


def built_ordering(flags, levels=0, balance=0.2):
    with _ephemeral_strat() as strat:
        ret = lib.SCOTCH_stratGraphOrderBuild(
            byref(strat), lib.SCOTCH_Num(int(flags)), lib.SCOTCH_Num(levels), c_double(balance)
        )
        assert ret == 0
        return _saved_form(strat)


class TestMappingBuildStructure:
    def test_default_is_multilevel_with_recursive_inside(self):
        """The default = m{...} whose coarsest-level method is r{...}: the
        answer to "can I have multilevel AND recursive?" is "that IS the
        default"."""
        saved = built_mapping(StrategyFlags.DEFAULT)
        assert saved.startswith("m{")
        assert "low=r{" in saved

    def test_recursive_is_the_bare_framework(self):
        saved = built_mapping(StrategyFlags.RECURSIVE)
        assert saved.startswith("r{")
        assert "m{" in saved  # multilevel still used inside the separator search

    def test_quality_differs_and_works_harder(self):
        default = built_mapping(StrategyFlags.DEFAULT)
        quality = built_mapping(StrategyFlags.QUALITY)
        assert quality != default
        assert "move=200" in quality and "move=200" not in default
        assert quality.count("|") > default.count("|")  # 3-way select vs 2-way

    def test_balance_differs_from_default(self):
        assert built_mapping(StrategyFlags.BALANCE) != built_mapping(StrategyFlags.DEFAULT)

    def test_no_built_strategy_is_hollow(self):
        from pyscotch.strategy import _HOLLOW_SLOT_RE

        for flags in (
            StrategyFlags.DEFAULT,
            StrategyFlags.QUALITY,
            StrategyFlags.SPEED,
            StrategyFlags.BALANCE,
            StrategyFlags.RECURSIVE,
            StrategyFlags.SAFETY,
        ):
            saved = built_mapping(flags)
            assert saved.strip() and not _HOLLOW_SLOT_RE.search(saved), (
                f"flag {flags!r} built a hollow strategy: {saved[:80]}"
            )

    def test_upstream_pin_speed_equals_default(self):
        """KNOWN UPSTREAM BEHAVIOUR (pinned): the mapping builder never
        consults SCOTCH_STRATSPEED, so SPEED builds the byte-identical default
        — partition_fast() is structurally the default strategy. If this turns
        red, upstream started honouring SPEED for mapping: update the
        partition_fast() docs and QUESTIONS_FOR_SCOTCH_TEAM.md."""
        assert built_mapping(StrategyFlags.SPEED) == built_mapping(StrategyFlags.DEFAULT)


class TestOrderingBuildStructure:
    def test_default_is_compressed_nested_dissection(self):
        saved = built_ordering(StrategyFlags.DEFAULT)
        assert saved.startswith("c{")
        assert "n{sep=" in saved

    def test_speed_differs_from_default(self):
        assert built_ordering(StrategyFlags.SPEED) != built_ordering(StrategyFlags.DEFAULT)

    def test_upstream_pin_quality_equals_default(self):
        """KNOWN UPSTREAM BEHAVIOUR (pinned): the ordering builder never
        consults SCOTCH_STRATQUALITY, so QUALITY builds the byte-identical
        default — order_quality() is structurally the default. Mirror image of
        the mapping SPEED pin; same instructions if it turns red."""
        assert built_ordering(StrategyFlags.QUALITY) == built_ordering(StrategyFlags.DEFAULT)

    def test_no_built_ordering_is_hollow(self):
        from pyscotch.strategy import _HOLLOW_SLOT_RE

        for flags in (StrategyFlags.DEFAULT, StrategyFlags.SPEED, StrategyFlags.LEVEL_MAX):
            saved = built_ordering(flags, levels=3)
            assert saved.strip() and not _HOLLOW_SLOT_RE.search(saved)


class TestProbeClassifier:
    """The checker's probe, exercised directly on the canonical cases."""

    @pytest.mark.parametrize(
        "string,expected",
        [
            ("r{sep=gf}", {"mapping": "ok", "ordering": "invalid", "overlap": "ok"}),
            ("s", {"mapping": "invalid", "ordering": "ok", "overlap": "invalid"}),
            ("m", {"mapping": "hollow", "ordering": "invalid", "overlap": "hollow"}),
            (
                "r{job=t,map=t,poli=S,bal=0.05}",
                {"mapping": "hollow", "ordering": "invalid", "overlap": "invalid"},
            ),
        ],
    )
    def test_probe_matrix(self, string, expected):
        from pyscotch.strategy import _probe_graph_string

        assert _probe_graph_string(string) == expected
