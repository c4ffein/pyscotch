"""The AGREEMENT check: PyScotch's model of the strategy grammar (the typed
builder's tables) versus the grammar itself.

Every strategy Scotch builds for itself must parse under our tables with no
unknown method, no unknown parameter and every strategy slot filled — and our
rendering of the parsed tree must mean exactly the same thing to Scotch
(parse it, save it, byte-identical to the original). An upstream method or
parameter we do not model turns this file red instead of leaving the typed
builder silently stale. The same parser is the importer: Scotch's canonical
default in, a typed tree out, tweakable, renderable.
"""

from ctypes import byref, c_char_p, c_double

import pytest

from pyscotch import Strategy, StrategyFlags, libscotch as lib
from pyscotch.strategy import _ephemeral_strat, _quiet_stderr, _saved_form
from pyscotch.strategy_grammar import (
    DMAPPING,
    DORDERING,
    MAPPING,
    ORDERING,
    SEPARATION,
    Cond,
    Empty,
    GrammarError,
    HollowSlotError,
    Mapping,
    Select,
    Seq,
    UnknownMethodError,
    UnknownParameterError,
    parse,
)

N = lib.SCOTCH_Num
PARALLEL = lib.is_parallel()


def scotch_canonical(text, family):
    """Scotch's own reading of `text`: parse under `family`, save. None if rejected."""
    parser = getattr(
        lib,
        {
            MAPPING: "SCOTCH_stratGraphMap",
            ORDERING: "SCOTCH_stratGraphOrder",
            DMAPPING: "SCOTCH_stratDgraphMap",
            DORDERING: "SCOTCH_stratDgraphOrder",
        }[family],
    )
    with _ephemeral_strat() as s:
        with _quiet_stderr():
            rc = parser(byref(s), c_char_p(text.encode("utf-8")))
        return _saved_form(s).strip() if rc == 0 else None


def built(family, flags=0, levels=0):
    with _ephemeral_strat() as s:
        if family == MAPPING:
            rc = lib.SCOTCH_stratGraphMapBuild(byref(s), N(flags), N(4), c_double(0.01))
        elif family == ORDERING:
            rc = lib.SCOTCH_stratGraphOrderBuild(byref(s), N(flags), N(levels), c_double(0.2))
        elif family == DMAPPING:
            rc = lib.SCOTCH_stratDgraphMapBuild(byref(s), N(0), N(2), N(4), c_double(0.01))
        else:
            rc = lib.SCOTCH_stratDgraphOrderBuild(byref(s), N(0), N(2), N(0), c_double(0.2))
        assert rc == 0
        return _saved_form(s).strip()


SEQUENTIAL_DEFAULTS = [
    pytest.param(MAPPING, int(StrategyFlags.DEFAULT), 0, id="map-DEFAULT"),
    pytest.param(MAPPING, int(StrategyFlags.QUALITY), 0, id="map-QUALITY"),
    pytest.param(MAPPING, int(StrategyFlags.BALANCE), 0, id="map-BALANCE"),
    pytest.param(MAPPING, int(StrategyFlags.RECURSIVE), 0, id="map-RECURSIVE"),
    pytest.param(MAPPING, int(StrategyFlags.SAFETY), 0, id="map-SAFETY"),
    pytest.param(ORDERING, int(StrategyFlags.DEFAULT), 0, id="order-DEFAULT"),
    pytest.param(ORDERING, int(StrategyFlags.DEFAULT), 3, id="order-DEFAULT-lv3"),
    pytest.param(ORDERING, int(StrategyFlags.SPEED), 0, id="order-SPEED"),
    pytest.param(ORDERING, int(StrategyFlags.LEVEL_MAX), 3, id="order-LEVEL_MAX"),
]


def assert_agreement(saved, family):
    tree = parse(saved, family)  # no UnknownMethod/UnknownParameter/HollowSlot
    assert scotch_canonical(tree.render(), family) == saved, (
        "our rendering of the parsed tree means something else to Scotch"
    )
    return tree


class TestAgreementOnScotchDefaults:
    @pytest.mark.parametrize("family,flags,levels", SEQUENTIAL_DEFAULTS)
    def test_sequential_default(self, family, flags, levels):
        assert_agreement(built(family, flags, levels), family)

    @pytest.mark.skipif(not PARALLEL, reason="needs the parallel library")
    @pytest.mark.parametrize("family", [DMAPPING, DORDERING])
    def test_distributed_default(self, family):
        assert_agreement(built(family), family)

    def test_defaults_exercise_every_construct(self):
        """The corpus is only a real guard if it covers the grammar: the
        ordering default has selections with an EMPTY alternative and
        conditions without else; the mapping default has juxtaposition."""
        order = built(ORDERING, 0, 3)
        assert "(|" in order and "/(" in order and "?" in order and ";" in order
        assert "}f{" in built(MAPPING)  # juxtaposition: ...}f{...


class TestTableDrivenDetection:
    """No library call: the tables alone classify these."""

    @pytest.mark.parametrize(
        "text,family",
        [("m", MAPPING), ("r{sep=}", MAPPING), ("r", DMAPPING), ("n", DORDERING), ("n{ole=s,ose=s}", DORDERING)],
    )
    def test_hollow(self, text, family):
        with pytest.raises(HollowSlotError):
            parse(text, family)

    def test_unknown_parameter(self):
        with pytest.raises(UnknownParameterError, match="no parameter 'foo'"):
            parse("m{low=f,asc=f,foo=1}", MAPPING)

    def test_unknown_method(self):
        with pytest.raises(UnknownMethodError, match="no method 'y'"):
            parse("y", MAPPING)

    def test_wrong_family_is_unknown_method(self):
        """`h` (greedy growing) exists for separation/bipart, not ordering."""
        with pytest.raises(UnknownMethodError):
            parse("h", ORDERING)
        assert parse("h", SEPARATION).letter == "h"

    def test_trailing_input(self):
        with pytest.raises(GrammarError, match="trailing"):
            parse("r{sep=gf}}", MAPPING)

    def test_unknown_family(self):
        with pytest.raises(ValueError, match="unknown grammar family"):
            parse("s", "mesh")


class TestConstructs:
    def test_selection_with_empty_alternative(self):
        tree = parse("m{asc=(|f),low=f,vert=100}", MAPPING)
        asc = tree._children["asc"]
        assert isinstance(asc, Select) and isinstance(asc.nodes[0], Empty)
        assert scotch_canonical(tree.render(), MAPPING) == scotch_canonical("m{asc=(|f),low=f,vert=100}", MAPPING)

    def test_condition_without_else(self):
        text = "m{asc=(/((vert)>(10))?f;),low=f}"
        tree = parse(text, MAPPING)
        asc = tree._children["asc"]
        assert isinstance(asc, Cond) and asc.orelse is None and asc.test == "((vert)>(10))"
        assert scotch_canonical(tree.render(), MAPPING) == scotch_canonical(text, MAPPING)

    def test_condition_with_else(self):
        text = "m{asc=(/((vert)>(10))?f:x;),low=f}"
        tree = parse(text, MAPPING)
        assert isinstance(tree._children["asc"].orelse, Mapping.Ex)
        assert scotch_canonical(tree.render(), MAPPING) == scotch_canonical(text, MAPPING)

    def test_juxtaposition(self):
        tree = parse("r{sep=hf}", MAPPING)
        assert isinstance(tree._children["sep"], Seq)
        assert tree.render() == "r{sep=hf}"

    def test_value_types(self):
        tree = parse("m{asc=f{move=120,bal=0.05},low=f,type=h,vert=100,rat=0.8}", MAPPING)
        assert tree._values == {"type": "h", "vert": 100, "rat": 0.8}
        assert tree._children["asc"]._values == {"move": 120, "bal": 0.05}


class TestImporter:
    """Scotch's canonical default in, a typed tree out, tweak, render, use."""

    def test_tweak_the_default_and_run_it(self):
        default = built(MAPPING)
        tree = parse(default, MAPPING)
        tree._children["asc"]._children["org"]._values["move"] = 300  # deeper FM refinement
        tweaked = tree.render()
        assert tweaked != default and "move=300" in tweaked
        canonical = scotch_canonical(tweaked, MAPPING)
        assert canonical is not None and "move=300" in canonical
        Strategy(tweaked)  # and the construction-time checker is happy
