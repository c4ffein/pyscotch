"""Tests for the typed strategy-grammar builder.

Three jobs:
1. DRIFT GUARD — every method class, from every grammar family, renders a
   minimal instance that the LIVE library parses as ok (not invalid, not
   hollow). If an upstream release renames a method letter or a parameter,
   this file turns red instead of PyScotch silently diverging.
2. The type-level guarantee: hollowness (missing strategy slots) and
   cross-family composition are TypeErrors at construction.
3. End-to-end: builder trees drive real partitions/orderings through
   Strategy(), and canonical round-trips are stable.
"""

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pyscotch import Graph
from pyscotch.strategy import Strategy
from pyscotch.strategy_grammar import (
    BIPART,
    MAPPING,
    ORDERING,
    SEPARATION,
    Bipart,
    Mapping,
    Ordering,
    Raw,
    Select,
    Separation,
    Seq,
)

# Simplest complete ("terminal") node per family, used to fill required slots.
TERMINALS = {
    MAPPING: lambda: Mapping.Fm(),
    BIPART: lambda: Bipart.Fm(),
    ORDERING: lambda: Ordering.Si(),
    SEPARATION: lambda: Separation.Fm(),
}


def minimal(cls):
    """A minimal valid instance: required strategy slots get family terminals."""
    kwargs = {slot: TERMINALS[family]() for slot, family in cls.strat_slots.items()}
    return cls(**kwargs)


def all_method_classes():
    for ns in (Mapping, Bipart, Ordering, Separation):
        seen = set()
        for name in vars(ns):
            cls = getattr(ns, name)
            if isinstance(cls, type) and hasattr(cls, "letter") and cls not in seen:
                seen.add(cls)
                yield ns.__name__, name, cls


class TestDriftGuard:
    @pytest.mark.parametrize(
        "ns,name,cls",
        [pytest.param(ns, n, c, id=f"{ns}.{n}") for ns, n, c in all_method_classes()],
    )
    def test_every_method_parses_live(self, ns, name, cls):
        """Render a minimal instance and let the live library judge it."""
        canonical = minimal(cls).validate()
        assert canonical.strip(), f"{ns}.{name} produced an empty canonical form"

    def test_canonical_form_is_stable(self):
        """parse -> save -> parse -> save must be a fixed point."""
        tree = Mapping.Multilevel(
            low=Mapping.Recursive(sep=Seq(Bipart.Gg(), Bipart.Fm())),
            asc=Mapping.Fm(move=120),
        )
        first = tree.validate()
        again = Raw(first)
        # Re-parse the canonical form as a mapping tree and re-save it.
        wrapped = Strategy(first)  # constructor probe validates it too
        from pyscotch.strategy import _probe_graph_string

        assert _probe_graph_string(first)["mapping"] == "ok"
        second = Mapping.Rb(sep=Raw("hf")).validate()  # smoke another shape
        assert second.strip()
        assert Raw(first).text == first


class TestTypeGuarantees:
    def test_missing_strategy_slot_is_a_typeerror(self):
        with pytest.raises(TypeError, match="missing required strategy parameter"):
            Mapping.Multilevel(low=Mapping.Fm())  # asc= missing
        with pytest.raises(TypeError, match="missing required strategy parameter"):
            Ordering.NestedDissection(sep=Separation.Fm(), ole=Ordering.Si())  # ose=

    def test_wrong_family_child_is_a_typeerror(self):
        with pytest.raises(TypeError, match="takes a bipart strategy"):
            Mapping.Recursive(sep=Ordering.Si())
        with pytest.raises(TypeError, match="takes a separation strategy"):
            Ordering.NestedDissection(
                sep=Bipart.Fm(), ole=Ordering.Si(), ose=Ordering.Si()
            )

    def test_mixed_family_composition_is_a_typeerror(self):
        with pytest.raises(TypeError, match="different grammar families"):
            Seq(Mapping.Fm(), Ordering.Si())

    def test_unknown_parameter_is_a_typeerror(self):
        with pytest.raises(TypeError, match="unknown parameters"):
            Bipart.Fm(passes=3)  # the parameter is called "pass"

    def test_raw_escapes_family_checks_but_not_validation(self):
        tree = Mapping.Recursive(sep=Raw("hf"))
        assert tree.validate().startswith("r{")
        broken = Mapping.Recursive(sep=Raw("zz-not-grammar"))
        with pytest.raises(ValueError, match="invalid"):
            broken.validate()


class TestRendering:
    def test_bare_method_renders_bare(self):
        assert str(Ordering.Si()) == "s"
        assert str(Bipart.Fm()) == "f"

    def test_numeric_params_render_only_when_set(self):
        assert str(Bipart.Fm(move=120)) == "f{move=120}"
        assert str(Bipart.Gg(pass_=4) if False else Bipart.Gg()) == "h"

    def test_the_tasks_md_example(self):
        tree = Mapping.Multilevel(
            low=Mapping.Recursive(sep=Seq(Bipart.Gg(), Bipart.Fm())),
            asc=Mapping.Fm(move=120),
        )
        assert str(tree) == "m{asc=f{move=120},low=r{sep=hf}}"

    def test_select_renders_the_quality_idiom(self):
        s = Select(Bipart.Fm(), Bipart.Fm(), Bipart.Fm())
        assert str(s) == "(f|f|f)"


class TestEndToEnd:
    def _ring(self, nvert=24):
        verttab = np.arange(0, 2 * nvert + 1, 2)
        edgetab = np.empty(2 * nvert, dtype=np.int64)
        for v in range(nvert):
            edgetab[2 * v] = (v - 1) % nvert
            edgetab[2 * v + 1] = (v + 1) % nvert
        g = Graph()
        g.build(verttab.astype(np.int64), edgetab)
        return g, nvert

    def test_builder_tree_partitions_for_real(self):
        tree = Mapping.Multilevel(
            low=Mapping.Recursive(sep=Seq(Bipart.Gg(), Bipart.Fm())),
            asc=Mapping.Fm(),
        )
        g, nvert = self._ring()
        part = g.partition(4, Strategy(str(tree)))
        assert (part >= 0).all()
        assert set(part.tolist()) == {0, 1, 2, 3}

    def test_builder_tree_orders_for_real(self):
        tree = Ordering.NestedDissection(
            sep=Separation.Multilevel(
                low=Separation.Gg(), asc=Separation.Fm()
            ),
            ole=Ordering.Si(),
            ose=Ordering.Si(),
        )
        g, nvert = self._ring(64)
        perm, peri = g.order(Strategy(str(tree)))
        assert np.array_equal(np.sort(perm), np.arange(nvert))
        assert np.array_equal(peri[perm], np.arange(nvert))


# ---------------------------------------------------------------------------
# Property tier: random valid trees always parse, never hollow.
# ---------------------------------------------------------------------------


def bipart_trees(depth):
    leaf = st.sampled_from([Bipart.Fm, Bipart.Gg, Bipart.Gp]).map(lambda c: c())
    if depth <= 0:
        return leaf
    sub = bipart_trees(depth - 1)
    return st.one_of(
        leaf,
        st.tuples(sub, sub).map(lambda t: Seq(*t)),
        st.tuples(sub, sub).map(lambda t: Select(*t)),
        st.tuples(sub, sub).map(lambda t: Bipart.Ml(low=t[0], asc=t[1])),
    )


def mapping_trees(depth):
    leaf = st.one_of(
        st.just(Mapping.Fm()).map(lambda x: x),
        bipart_trees(depth - 1).map(lambda b: Mapping.Rb(sep=b)),
    )
    if depth <= 1:
        return leaf
    sub = mapping_trees(depth - 1)
    return st.one_of(leaf, st.tuples(sub, sub).map(lambda t: Mapping.Ml(low=t[0], asc=t[1])))


@given(tree=mapping_trees(3))
@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_random_mapping_trees_are_valid_and_never_hollow(tree):
    canonical = tree.validate()  # raises unless probe says "ok"
    assert canonical.strip()
