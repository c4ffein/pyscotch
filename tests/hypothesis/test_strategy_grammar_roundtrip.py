"""Property tier for the strategy grammar: for ANY tree the typed builder can
express, Scotch reads our rendering, our parser reads Scotch's rendering, and
the two agree.

    tree --render--> s --Scotch parse+save--> c1 --parse()--> tree' --render--> s'
                                                              --Scotch parse+save--> c2
    c1 == c2   (fixpoint through both parsers; compared on SCOTCH's canonical
               form, since Scotch reorders parameters and normalizes numbers)

This generalizes tests/pyscotch_base/test_strategy_parse.py — which checks
the eleven strings Scotch writes for itself — to the whole language the
builder covers: every family, populated value parameters, Seq/Select with
empty alternatives, conditions. Generated trees are complete and well-formed
by construction, so the Scotch round-trip is safe in-process (upstream only
faults on implicit slots and malformed syntax).
"""

from ctypes import byref, c_char_p

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from pyscotch import libscotch as lib
from pyscotch.strategy import _ephemeral_strat, _quiet_stderr, _saved_form
from pyscotch.strategy_grammar import (
    DMAPPING,
    DORDERING,
    MAPPING,
    NAMESPACES,
    ORDERING,
    Cond,
    Empty,
    GrammarError,
    Select,
    Seq,
    parse,
)

PARALLEL = lib.is_parallel()
TOP_LEVEL_PARSERS = {
    MAPPING: "SCOTCH_stratGraphMap",
    ORDERING: "SCOTCH_stratGraphOrder",
    DMAPPING: "SCOTCH_stratDgraphMap",
    DORDERING: "SCOTCH_stratDgraphOrder",
}

# Case-valued parameters: only values Scotch's own defaults use, per method
# class, so a rejection is never "we invented a letter". Unlisted case params
# are simply not generated.
CASE_VALUES = {
    ("Ml", "type"): ["h"],
    ("Fm", "type"): ["b"],
    ("Df", "type"): ["b"],
    ("Rb", "poli"): ["S"],
    ("Rb", "job"): ["t"],
    ("Rb", "map"): ["t"],
    ("Ml", "fold"): ["d"],
}
# Condition variables common to every grammar that has a condition table
# (kdgraph — DMAPPING — has none, so no Cond is generated at that level).
COND_VARS = ["vert", "levl"]
COND_FREE = {DMAPPING}

INTS = st.integers(min_value=1, max_value=100)
FLOATS = st.sampled_from([0.01, 0.05, 0.1, 0.2, 0.5, 0.8, 0.95, 1.0])


def method_classes(family):
    seen, out = set(), []
    for name in vars(NAMESPACES[family]):
        cls = getattr(NAMESPACES[family], name)
        if isinstance(cls, type) and hasattr(cls, "letter") and cls not in seen:
            seen.add(cls)
            out.append(cls)
    return out


def value_kwargs(cls):
    """Optional value parameters, drawn by type (case values from the inventory)."""
    optional = {}
    for param, typ in cls.value_params.items():
        if typ is int:
            optional[param] = INTS
        elif typ is float:
            optional[param] = FLOATS
        elif (cls.__name__, param) in CASE_VALUES:
            optional[param] = st.sampled_from(CASE_VALUES[(cls.__name__, param)])
    return optional


def trees(family, depth):
    """Random typed trees of `family`, at most `depth` method levels deep."""
    classes = method_classes(family)
    leaves = [c for c in classes if not c.strat_slots]

    def build(cls):
        slots = {slot: trees(fam, depth - 1) for slot, fam in cls.strat_slots.items()}
        return st.fixed_dictionaries(slots, optional=value_kwargs(cls)).map(lambda kw: cls(**kw))

    if depth <= 0:
        return st.one_of([build(c) for c in leaves])
    method = st.one_of([build(c) for c in classes])
    sub = trees(family, depth - 1)
    combinators = [
        method,
        st.tuples(sub, sub).map(lambda t: Seq(*t)),
        st.tuples(sub, sub).map(lambda t: Select(*t)),
        sub.map(lambda t: Select(Empty(), t)),
    ]
    if family not in COND_FREE:
        test = st.tuples(st.sampled_from(COND_VARS), st.sampled_from([">", "<", "="]), INTS).map(
            lambda t: f"(({t[0]}){t[1]}({t[2]}))"
        )
        combinators.append(st.tuples(test, sub).map(lambda t: Cond(t[0], t[1])))
        combinators.append(st.tuples(test, sub, sub).map(lambda t: Cond(t[0], t[1], t[2])))
    return st.one_of(combinators)


def scotch_canonical(text, family):
    parser = getattr(lib, TOP_LEVEL_PARSERS[family])
    with _ephemeral_strat() as s:
        with _quiet_stderr():
            rc = parser(byref(s), c_char_p(text.encode("utf-8")))
        return _saved_form(s).strip() if rc == 0 else None


def check_roundtrip(tree, family):
    rendered = tree.render()
    c1 = scotch_canonical(rendered, family)
    assert c1 is not None, f"Scotch rejects the builder's rendering: {rendered}"
    try:
        reparsed = parse(c1, family)
    except GrammarError as e:
        raise AssertionError(f"our parser rejects Scotch's canonical form: {e}\n  canonical: {c1}") from None
    # Our own fixpoint: re-rendering what we parsed from ourselves is stable.
    assert parse(rendered, family).render() == rendered
    c2 = scotch_canonical(reparsed.render(), family)
    assert c2 == c1, f"meaning drifted through parse():\n  c1: {c1}\n  c2: {c2}"


PROPERTY = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@PROPERTY
@given(trees(MAPPING, 3))
def test_mapping_trees_roundtrip(tree):
    check_roundtrip(tree, MAPPING)


@PROPERTY
@given(trees(ORDERING, 3))
def test_ordering_trees_roundtrip(tree):
    check_roundtrip(tree, ORDERING)


@pytest.mark.skipif(not PARALLEL, reason="distributed grammars need the parallel library")
@PROPERTY
@given(trees(DMAPPING, 3))
def test_dmapping_trees_roundtrip(tree):
    check_roundtrip(tree, DMAPPING)


@pytest.mark.skipif(not PARALLEL, reason="distributed grammars need the parallel library")
@PROPERTY
@given(trees(DORDERING, 3))
def test_dordering_trees_roundtrip(tree):
    check_roundtrip(tree, DORDERING)
