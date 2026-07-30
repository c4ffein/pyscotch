"""Typed builder for Scotch strategy strings — hollowness made unrepresentable.

A typed, composable way to *write* standard Scotch strategy strings:

    from pyscotch.strategy_grammar import Mapping, Bipart
    tree = Mapping.Multilevel(
        low=Mapping.Recursive(sep=Bipart.Seq(Bipart.Gg(), Bipart.Fm())),
        asc=Mapping.Fm(move=120),
    )
    strat = Strategy(str(tree))     # output is a PLAIN Scotch string

Principles (see tasks.md for the full design):

1. **Scotch stays the sole semantic authority.** ``str(tree)`` is a standard
   grammar string, nothing more; no reinterpretation, no new semantics.
   Numeric/case parameters are rendered only when you set them, so Scotch's
   own defaults apply — upstream's defaults are never re-encoded here.
2. **Hollowness unrepresentable.** Strategy-valued parameters (``m``'s
   ``low=``/``asc=``, ``r``'s ``sep=``, ``n``'s ``sep=``/``ole=``/``ose=``,
   ...) are REQUIRED constructor arguments: the type system cannot express a
   stratdummy slot. (Bare strings can — which is why Strategy() also probes.)
3. **Validated against the live library.** ``validate()`` renders the tree,
   parses it with Scotch's own parser for the tree's grammar family, and
   round-trips it through SCOTCH_stratSave to assert nothing is hollow.

Method classes are named after upstream's own routine suffixes
(``kgraphMapMl`` -> ``Mapping.Ml``, aliased ``Mapping.Multilevel``), one
namespace per grammar family; the parameter inventory mirrors the
``*_st.c`` method tables. Condition constructs (``/(test)? s1 : s2 ;``) are
not modelled — use ``Raw`` for those subtrees.
"""

from __future__ import annotations

from typing import Optional, Union

# Grammar families. A method's strategy-valued slots name the family their
# children must belong to; Raw/Seq/Select adapt to any family.
MAPPING = "mapping"
BIPART = "bipart"
ORDERING = "ordering"
SEPARATION = "separation"

#: Families PyScotch can parse-validate directly (top-level grammars). Bipart
#: and separation trees only occur nested inside mapping/ordering trees, so
#: they are validated in context (see validate()).
_TOP_LEVEL = {MAPPING, ORDERING}


class Node:
    """Base of every strategy-tree node. Renders via str()."""

    family: Optional[str] = None  # None = adapts to any family (Raw, ...)

    def render(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.render()

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.render()!r})"

    def validate(self) -> str:
        """Parse-validate this tree against the live library; return the
        canonical (stratSave) form. Raises ValueError if the rendered string
        does not parse under the tree's grammar family, or is hollow.

        Only mapping and ordering trees are top-level grammars; a bipart or
        separation subtree is validated by wrapping it in the smallest
        enclosing method of a top-level family.
        """
        from .strategy import _probe_graph_string

        node = self
        if self.family == BIPART:
            node = Mapping.Rb(sep=self)
        elif self.family == SEPARATION:
            node = Ordering.Nd(sep=self, ole=Ordering.Si(), ose=Ordering.Si())
        elif self.family is None:
            raise ValueError(
                "This node adapts to any grammar family; validate it inside a "
                "typed tree (or via Strategy(str(tree)))."
            )
        probe = _probe_graph_string(node.render())
        target = node.family
        status = probe.get(target)
        if status != "ok":
            raise ValueError(
                f"Rendered strategy {node.render()!r} is {status} under the "
                f"{target} grammar (probe: {probe})."
            )
        from .strategy import _ephemeral_strat, _saved_form
        from . import libscotch as lib
        from ctypes import byref, c_char_p

        parser = {
            MAPPING: lib.SCOTCH_stratGraphMap,
            ORDERING: lib.SCOTCH_stratGraphOrder,
        }[target]
        with _ephemeral_strat() as strat:
            parser(byref(strat), c_char_p(node.render().encode("utf-8")))
            return _saved_form(strat)


class Raw(Node):
    """A verbatim string subtree — the explicit, localized escape hatch.

    Use it when upstream's grammar has evolved past the typed classes, or for
    constructs the builder does not model (conditions). The rendered whole
    still goes through Strategy()'s probe, so even a Raw part cannot be
    silently hollow at the top level.
    """

    family = None

    def __init__(self, text: str):
        if not isinstance(text, str) or not text:
            raise ValueError("Raw() takes a non-empty strategy-string fragment")
        self.text = text

    def render(self) -> str:
        return self.text


def _families_of(nodes):
    fams = {n.family for n in nodes if n.family is not None}
    if len(fams) > 1:
        raise TypeError(f"nodes from different grammar families composed together: {fams}")
    return fams.pop() if fams else None


class Seq(Node):
    """Concatenation: run the strategies in sequence (grammar juxtaposition,
    e.g. Seq(Gg(), Fm()) renders "hf" — graph-growing then refinement)."""

    def __init__(self, *nodes: Node):
        if not nodes:
            raise ValueError("Seq() needs at least one node")
        self.nodes = nodes
        self.family = _families_of(nodes)

    def render(self) -> str:
        return "".join(n.render() for n in self.nodes)


class Select(Node):
    """Selection: run every alternative, keep the best result (the grammar's
    '|' operator — the construct Scotch's own QUALITY preset is built from).
    Because the PRNG stream advances between branches, identical alternatives
    are independent attempts: Select(m, m, m) is best-of-three."""

    def __init__(self, *nodes: Node):
        if len(nodes) < 2:
            raise ValueError("Select() needs at least two alternatives")
        self.nodes = nodes
        self.family = _families_of(nodes)

    def render(self) -> str:
        return "(" + "|".join(n.render() for n in self.nodes) + ")"


def _method(family_tag, letter, name, strat_slots, value_params, doc, alias=None):
    """Build one method class from its *_st.c table row.

    strat_slots: {param_name: child_family} — REQUIRED keyword arguments.
    value_params: {param_name: type} — optional; rendered only when set, so
    Scotch's own defaults apply otherwise.
    """

    def __init__(self, **kwargs):
        self._children = {}
        self._values = {}
        for slot, child_family in strat_slots.items():
            if slot not in kwargs:
                raise TypeError(
                    f"{name}() missing required strategy parameter {slot!r} — "
                    "implicit strategy slots are do-nothing dummies in Scotch, "
                    "so the builder makes them mandatory (use Raw(...) to "
                    "escape-hatch a slot)."
                )
            child = kwargs.pop(slot)
            if not isinstance(child, Node):
                raise TypeError(f"{name}({slot}=...) takes a strategy node, got {type(child)}")
            if child.family is not None and child_family is not None and child.family != child_family:
                raise TypeError(
                    f"{name}({slot}=...) takes a {child_family} strategy, "
                    f"got a {child.family} one"
                )
            self._children[slot] = child
        for param, typ in value_params.items():
            if param in kwargs:
                value = kwargs.pop(param)
                if typ in (int, float) and not isinstance(value, (int, float)):
                    raise TypeError(f"{name}({param}=...) takes {typ.__name__}")
                self._values[param] = value
        if kwargs:
            raise TypeError(f"{name}() got unknown parameters {sorted(kwargs)}")

    def render(self) -> str:
        parts = [f"{k}={v.render()}" for k, v in sorted(self._children.items())]
        parts += [f"{k}={v}" for k, v in sorted(self._values.items())]
        return letter + ("{" + ",".join(parts) + "}" if parts else "")

    cls = type(
        name,
        (Node,),
        {
            "__init__": __init__,
            "render": render,
            "family": family_tag,
            "letter": letter,
            "strat_slots": dict(strat_slots),
            "value_params": dict(value_params),
            "__doc__": doc,
        },
    )
    return cls


class _Namespace:
    """Just a named bag of method classes (one per grammar family)."""


def _build_namespace(ns_name, family_tag, rows):
    ns = type(ns_name, (_Namespace,), {"__doc__": f"{family_tag} grammar methods"})
    for letter, name, strat_slots, value_params, doc, aliases in rows:
        cls = _method(family_tag, letter, name, strat_slots, value_params, doc)
        setattr(ns, name, cls)
        for alias in aliases:
            setattr(ns, alias, cls)
    return ns


_NUM = int
_DBL = float
_CASE = str

# Method tables, mirroring external/scotch/src/libscotch/*_st.c exactly
# (letters, parameter names and kinds). The drift-guard test renders a minimal
# instance of every class and parses it with the live library, so upstream
# grammar changes turn the suite red here instead of silently diverging.

Mapping = _build_namespace(
    "Mapping",
    MAPPING,
    [
        ("b", "Bd", {"bnd": MAPPING, "org": MAPPING}, {"width": _NUM},
         "Band method: applies bnd= to a band around the frontier, org= elsewhere.", ["Band"]),
        ("c", "Cp", {}, {},
         "Copy the current partition (no parameters).", ["Copy"]),
        ("d", "Df", {}, {"pass": _NUM, "dif": _DBL, "rem": _DBL},
         "Diffusion method.", ["Diffusion"]),
        ("x", "Ex", {}, {"bal": _DBL},
         "Exactifier: enforce load balance.", ["Exactify"]),
        ("f", "Fm", {}, {"move": _NUM, "pass": _NUM, "bal": _DBL},
         "Fiduccia-Mattheyses refinement.", ["FiducciaMattheyses"]),
        ("m", "Ml", {"low": MAPPING, "asc": MAPPING}, {"vert": _NUM, "rat": _DBL, "type": _CASE},
         "Multilevel framework: low= at the coarsest level, asc= while uncoarsening.", ["Multilevel"]),
        ("r", "Rb", {"sep": BIPART}, {"bal": _DBL, "job": _CASE, "map": _CASE, "poli": _CASE},
         "Recursive bipartitioning; sep= is a BIPARTITIONING strategy.", ["Recursive"]),
    ],
)

Bipart = _build_namespace(
    "Bipart",
    BIPART,
    [
        ("b", "Bd", {"bnd": BIPART, "org": BIPART}, {"width": _NUM}, "Band method.", ["Band"]),
        ("d", "Df", {}, {"pass": _NUM, "type": _CASE}, "Diffusion method.", ["Diffusion"]),
        ("x", "Ex", {}, {}, "Exactifier.", ["Exactify"]),
        ("f", "Fm", {}, {"move": _NUM, "pass": _NUM, "bal": _DBL, "type": _CASE},
         "Fiduccia-Mattheyses refinement.", ["FiducciaMattheyses"]),
        ("a", "Ga", {}, {"pass": _NUM, "pop": _NUM}, "Genetic algorithm.", ["Genetic"]),
        ("h", "Gg", {}, {"pass": _NUM}, "Greedy graph growing.", ["GreedyGrowing"]),
        ("g", "Gp", {}, {"pass": _NUM}, "Gibbs-Poole-Stockmeyer growing.", []),
        ("m", "Ml", {"low": BIPART, "asc": BIPART}, {"vert": _NUM, "rat": _DBL},
         "Multilevel bipartitioning framework.", ["Multilevel"]),
        ("z", "Zr", {}, {}, "Zero method: assign everything to part 0.", ["Zero"]),
    ],
)

Ordering = _build_namespace(
    "Ordering",
    ORDERING,
    [
        ("b", "Bl", {"strat": ORDERING}, {"cmin": _NUM},
         "Block splitting post-processing of strat=.", ["Blocks"]),
        ("o", "Cc", {"strat": ORDERING}, {},
         "Order connected components separately with strat=.", ["Components"]),
        ("c", "Cp", {"cpr": ORDERING, "unc": ORDERING}, {"rat": _DBL},
         "Compression: cpr= orders the compressed graph, unc= the uncompressed.", ["Compress"]),
        ("g", "Gp", {}, {"pass": _NUM}, "Gibbs-Poole-Stockmeyer.", []),
        ("d", "Hd", {}, {"cmin": _NUM, "cmax": _NUM, "frat": _DBL},
         "Halo approximate minimum degree.", ["HaloMinDegree"]),
        ("f", "Hf", {}, {"cmin": _NUM, "cmax": _NUM, "frat": _DBL},
         "Halo approximate minimum fill.", ["HaloMinFill"]),
        ("k", "Kp", {"strat": MAPPING}, {"siz": _NUM},
         "Block ordering from a k-way partition computed by strat= "
         "(a MAPPING strategy — established empirically).", []),
        ("n", "Nd", {"sep": SEPARATION, "ole": ORDERING, "ose": ORDERING}, {},
         "Nested dissection: sep= is a SEPARATION strategy; ole=/ose= order "
         "the leaves / the separators.", ["NestedDissection"]),
        ("s", "Si", {}, {}, "Simple: the natural order (identity).", ["Simple"]),
    ],
)

Separation = _build_namespace(
    "Separation",
    SEPARATION,
    [
        ("b", "Bd", {"bnd": SEPARATION, "org": SEPARATION}, {"width": _NUM}, "Band method.", ["Band"]),
        ("e", "Es", {"strat": BIPART}, {"type": _CASE},
         "Edge separation: derive a vertex separator from a BIPARTITIONING "
         "strategy (established empirically: bipart-only methods parse in "
         "this slot, separation-only ones do not).", []),
        ("f", "Fm", {}, {"move": _NUM, "pass": _NUM, "bal": _DBL},
         "Fiduccia-Mattheyses refinement.", ["FiducciaMattheyses"]),
        ("h", "Gg", {}, {"pass": _NUM}, "Greedy graph growing.", ["GreedyGrowing"]),
        ("g", "Gp", {}, {"pass": _NUM}, "Gibbs-Poole-Stockmeyer growing.", []),
        ("m", "Ml", {"low": SEPARATION, "asc": SEPARATION}, {"vert": _NUM, "rat": _DBL, "type": _CASE},
         "Multilevel separation framework.", ["Multilevel"]),
        ("v", "Vw", {}, {}, "Vertex-weighted greedy.", []),
        ("z", "Zr", {}, {}, "Zero method: empty separator.", ["Zero"]),
    ],
)
