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

from typing import Optional

# Grammar families. A method's strategy-valued slots name the family their
# children must belong to; Raw/Seq/Select adapt to any family.
MAPPING = "mapping"
BIPART = "bipart"
ORDERING = "ordering"
SEPARATION = "separation"
# PT-Scotch (distributed) grammars, parsed by libptscotch.
DMAPPING = "dmapping"
DBIPART = "dbipart"
DORDERING = "dordering"
DSEPARATION = "dseparation"

#: Families PyScotch can parse-validate directly (top-level grammars). Bipart
#: and separation trees only occur nested inside mapping/ordering trees, so
#: they are validated in context (see validate()).
_TOP_LEVEL = {MAPPING, ORDERING, DMAPPING, DORDERING}


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
        elif self.family == DBIPART:
            node = DMapping.Rb(sep=self, seq=Mapping.Cp())
        elif self.family == DSEPARATION:
            node = DOrdering.Nd(sep=self, ole=DOrdering.Si(), ose=DOrdering.Si(), osq=Ordering.Si())
        elif self.family is None:
            raise ValueError(
                "This node adapts to any grammar family; validate it inside a typed tree (or via Strategy(str(tree)))."
            )
        target = node.family
        if target in (DMAPPING, DORDERING):
            from .strategy import _probe_dgraph_string

            probe = _probe_dgraph_string(node.render())  # sandboxed, see strategy.py
        else:
            probe = _probe_graph_string(node.render())
        status = probe.get(target)
        if status != "ok":
            raise ValueError(
                f"Rendered strategy {node.render()!r} is {status} under the {target} grammar (probe: {probe})."
            )
        from ctypes import byref, c_char_p

        from . import libscotch as lib
        from .strategy import _ephemeral_strat, _saved_form

        # Looked up by name: the PT-Scotch parsers only exist on the parallel
        # library, and a sequential build must still validate sequential trees.
        parser = getattr(
            lib,
            {
                MAPPING: "SCOTCH_stratGraphMap",
                ORDERING: "SCOTCH_stratGraphOrder",
                DMAPPING: "SCOTCH_stratDgraphMap",
                DORDERING: "SCOTCH_stratDgraphOrder",
            }[target],
        )
        # In-process stratSave is safe here: the probe just proved the strategy
        # complete, and upstream only faults on implicit slots.
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
                raise TypeError(f"{name}({slot}=...) takes a {child_family} strategy, got a {child.family} one")
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
        (
            "b",
            "Bd",
            {"bnd": MAPPING, "org": MAPPING},
            {"width": _NUM},
            "Band method: applies bnd= to a band around the frontier, org= elsewhere.",
            ["Band"],
        ),
        ("c", "Cp", {}, {}, "Copy the current partition (no parameters).", ["Copy"]),
        ("d", "Df", {}, {"pass": _NUM, "dif": _DBL, "rem": _DBL}, "Diffusion method.", ["Diffusion"]),
        ("x", "Ex", {}, {"bal": _DBL}, "Exactifier: enforce load balance.", ["Exactify"]),
        (
            "f",
            "Fm",
            {},
            {"move": _NUM, "pass": _NUM, "bal": _DBL},
            "Fiduccia-Mattheyses refinement.",
            ["FiducciaMattheyses"],
        ),
        (
            "m",
            "Ml",
            {"low": MAPPING, "asc": MAPPING},
            {"vert": _NUM, "rat": _DBL, "type": _CASE},
            "Multilevel framework: low= at the coarsest level, asc= while uncoarsening.",
            ["Multilevel"],
        ),
        (
            "r",
            "Rb",
            {"sep": BIPART},
            {"bal": _DBL, "job": _CASE, "map": _CASE, "poli": _CASE},
            "Recursive bipartitioning; sep= is a BIPARTITIONING strategy.",
            ["Recursive"],
        ),
    ],
)

Bipart = _build_namespace(
    "Bipart",
    BIPART,
    [
        ("b", "Bd", {"bnd": BIPART, "org": BIPART}, {"width": _NUM}, "Band method.", ["Band"]),
        ("d", "Df", {}, {"pass": _NUM, "type": _CASE}, "Diffusion method.", ["Diffusion"]),
        ("x", "Ex", {}, {}, "Exactifier.", ["Exactify"]),
        (
            "f",
            "Fm",
            {},
            {"move": _NUM, "pass": _NUM, "bal": _DBL, "type": _CASE},
            "Fiduccia-Mattheyses refinement.",
            ["FiducciaMattheyses"],
        ),
        ("a", "Ga", {}, {"pass": _NUM, "pop": _NUM}, "Genetic algorithm.", ["Genetic"]),
        ("h", "Gg", {}, {"pass": _NUM}, "Greedy graph growing.", ["GreedyGrowing"]),
        ("g", "Gp", {}, {"pass": _NUM}, "Gibbs-Poole-Stockmeyer growing.", []),
        (
            "m",
            "Ml",
            {"low": BIPART, "asc": BIPART},
            {"vert": _NUM, "rat": _DBL},
            "Multilevel bipartitioning framework.",
            ["Multilevel"],
        ),
        ("z", "Zr", {}, {}, "Zero method: assign everything to part 0.", ["Zero"]),
    ],
)

Ordering = _build_namespace(
    "Ordering",
    ORDERING,
    [
        ("b", "Bl", {"strat": ORDERING}, {"cmin": _NUM}, "Block splitting post-processing of strat=.", ["Blocks"]),
        ("o", "Cc", {"strat": ORDERING}, {}, "Order connected components separately with strat=.", ["Components"]),
        (
            "c",
            "Cp",
            {"cpr": ORDERING, "unc": ORDERING},
            {"rat": _DBL},
            "Compression: cpr= orders the compressed graph, unc= the uncompressed.",
            ["Compress"],
        ),
        ("g", "Gp", {}, {"pass": _NUM}, "Gibbs-Poole-Stockmeyer.", []),
        (
            "d",
            "Hd",
            {},
            {"cmin": _NUM, "cmax": _NUM, "frat": _DBL},
            "Halo approximate minimum degree.",
            ["HaloMinDegree"],
        ),
        ("f", "Hf", {}, {"cmin": _NUM, "cmax": _NUM, "frat": _DBL}, "Halo approximate minimum fill.", ["HaloMinFill"]),
        (
            "k",
            "Kp",
            {"strat": MAPPING},
            {"siz": _NUM},
            "Block ordering from a k-way partition computed by strat= (a MAPPING strategy — established empirically).",
            [],
        ),
        (
            "n",
            "Nd",
            {"sep": SEPARATION, "ole": ORDERING, "ose": ORDERING},
            {},
            "Nested dissection: sep= is a SEPARATION strategy; ole=/ose= order the leaves / the separators.",
            ["NestedDissection"],
        ),
        ("s", "Si", {}, {}, "Simple: the natural order (identity).", ["Simple"]),
    ],
)

Separation = _build_namespace(
    "Separation",
    SEPARATION,
    [
        ("b", "Bd", {"bnd": SEPARATION, "org": SEPARATION}, {"width": _NUM}, "Band method.", ["Band"]),
        (
            "e",
            "Es",
            {"strat": BIPART},
            {"type": _CASE},
            "Edge separation: derive a vertex separator from a BIPARTITIONING "
            "strategy (established empirically: bipart-only methods parse in "
            "this slot, separation-only ones do not).",
            [],
        ),
        (
            "f",
            "Fm",
            {},
            {"move": _NUM, "pass": _NUM, "bal": _DBL},
            "Fiduccia-Mattheyses refinement.",
            ["FiducciaMattheyses"],
        ),
        ("h", "Gg", {}, {"pass": _NUM}, "Greedy graph growing.", ["GreedyGrowing"]),
        ("g", "Gp", {}, {"pass": _NUM}, "Gibbs-Poole-Stockmeyer growing.", []),
        (
            "m",
            "Ml",
            {"low": SEPARATION, "asc": SEPARATION},
            {"vert": _NUM, "rat": _DBL, "type": _CASE},
            "Multilevel separation framework.",
            ["Multilevel"],
        ),
        ("v", "Vw", {}, {}, "Vertex-weighted greedy.", []),
        ("z", "Zr", {}, {}, "Zero method: empty separator.", ["Zero"]),
    ],
)


# ---------------------------------------------------------------------------
# PT-Scotch (distributed) method tables — kdgraph_map_st.c, bdgraph_bipart_st.c,
# hdgraph_order_st.c, vdgraph_separate_st.c. Cross-family slots are exactly as
# upstream declares them: a distributed `q` wraps a SEQUENTIAL strategy, a
# distributed `n`'s osq= is a sequential ordering, kdgraph `r`'s seq= is a
# sequential mapping.
# ---------------------------------------------------------------------------

DMapping = _build_namespace(
    "DMapping",
    DMAPPING,
    [
        (
            "r",
            "Rb",
            {"sep": DBIPART, "seq": MAPPING},
            {"bal": _DBL},
            "Distributed recursive bipartitioning: sep= is a DISTRIBUTED bipartitioning "
            "strategy, seq= the SEQUENTIAL mapping strategy used once the graph is gathered.",
            ["Recursive"],
        ),
    ],
)

DBipart = _build_namespace(
    "DBipart",
    DBIPART,
    [
        ("b", "Bd", {"bnd": DBIPART, "org": DBIPART}, {"width": _NUM}, "Band method.", ["Band"]),
        ("d", "Df", {}, {"pass": _NUM, "dif": _DBL, "rem": _DBL, "type": _CASE}, "Diffusion method.", ["Diffusion"]),
        ("x", "Ex", {}, {"sbbt": _NUM, "bal": _DBL}, "Exactifier.", ["Exactify"]),
        (
            "m",
            "Ml",
            {"asc": DBIPART, "low": DBIPART, "seq": DBIPART},
            {"pass": _NUM, "vert": _NUM, "dvert": _NUM, "fold": _CASE, "rat": _DBL},
            "Distributed multilevel framework (seq= applies after folding).",
            ["Multilevel"],
        ),
        (
            "q",
            "Sq",
            {"strat": BIPART},
            {},
            "Sequential: gather and run a SEQUENTIAL bipartitioning strategy.",
            ["Sequential"],
        ),
        ("z", "Zr", {}, {}, "Zero method: everything in part 0.", ["Zero"]),
    ],
)

DOrdering = _build_namespace(
    "DOrdering",
    DORDERING,
    [
        (
            "n",
            "Nd",
            {"sep": DSEPARATION, "ole": DORDERING, "ose": DORDERING, "osq": ORDERING},
            {},
            "Distributed nested dissection: sep= a DISTRIBUTED separation strategy, ole=/ose= "
            "distributed orderings for leaves/separators, osq= the SEQUENTIAL ordering once gathered.",
            ["NestedDissection"],
        ),
        ("s", "Si", {}, {}, "Simple: the natural order.", ["Simple"]),
        (
            "q",
            "Sq",
            {"strat": ORDERING},
            {},
            "Sequential: gather and run a SEQUENTIAL ordering strategy.",
            ["Sequential"],
        ),
    ],
)

DSeparation = _build_namespace(
    "DSeparation",
    DSEPARATION,
    [
        ("b", "Bd", {"strat": DSEPARATION}, {"width": _NUM}, "Band method.", ["Band"]),
        (
            "d",
            "Df",
            {},
            {"part": _NUM, "pass": _NUM, "bal": _DBL, "dif": _DBL, "rem": _DBL},
            "Diffusion method.",
            ["Diffusion"],
        ),
        (
            "m",
            "Ml",
            {"asc": DSEPARATION, "low": DSEPARATION, "seq": DSEPARATION},
            {"pass": _NUM, "vert": _NUM, "dvert": _NUM, "fold": _CASE, "rat": _DBL},
            "Distributed multilevel separation framework.",
            ["Multilevel"],
        ),
        (
            "q",
            "Sq",
            {"strat": SEPARATION},
            {},
            "Sequential: gather and run a SEQUENTIAL separation strategy.",
            ["Sequential"],
        ),
        ("z", "Zr", {}, {}, "Zero method: empty separator.", ["Zero"]),
    ],
)

NAMESPACES = {
    MAPPING: Mapping,
    BIPART: Bipart,
    ORDERING: Ordering,
    SEPARATION: Separation,
    DMAPPING: DMapping,
    DBIPART: DBipart,
    DORDERING: DOrdering,
    DSEPARATION: DSeparation,
}


def _letters(ns):
    out = {}
    for name in vars(ns):
        cls = getattr(ns, name)
        if isinstance(cls, type) and hasattr(cls, "letter"):
            out[cls.letter] = cls
    return out


_FAMILY_METHODS = {family: _letters(ns) for family, ns in NAMESPACES.items()}


# ---------------------------------------------------------------------------
# Parsing Scotch strategy strings into typed trees.
#
# This is the AGREEMENT check between PyScotch's model of the grammar (the
# tables above) and the grammar itself: a string Scotch produced — above all
# its own built-in defaults — must parse here with no unknown method, no
# unknown parameter and every strategy slot filled. An upstream method or
# parameter we do not model surfaces as an error instead of a silently stale
# builder. It doubles as the importer: parse Scotch's canonical default,
# tweak it typed, render it back.
#
# Parsing is table-driven by necessity: `type=h` (a case value) and `low=h` (a
# strategy) are lexically identical; only the method table says which is which.
# ---------------------------------------------------------------------------


class GrammarError(ValueError):
    """The string does not fit PyScotch's model of the strategy grammar."""


class UnknownMethodError(GrammarError):
    """A method letter the family's table does not list (upstream added one?)."""


class UnknownParameterError(GrammarError):
    """A parameter the method's table does not list (upstream added one?)."""


class HollowSlotError(GrammarError):
    """A strategy-valued slot is missing or empty: a stratdummy in Scotch."""


class Empty(Node):
    """The empty strategy (Scotch's STRATNODEEMPTY): legitimate as a selection
    alternative — `(|h{pass=10})` appears in the built-in ordering default —
    or as a missing else-branch. In a method's strategy slot it is hollow."""

    family = None

    def render(self) -> str:
        return ""


class Cond(Node):
    """A condition node `/(test)?then:else;` — the test is kept as opaque text
    (its own small expression grammar over graph attributes such as vert,
    edge, levl, load, proc, rank); then/else are typed strategies."""

    def __init__(self, test: str, then: Node, orelse: Optional[Node] = None):
        if not (test.startswith("(") and test.endswith(")")):
            raise GrammarError(f"condition test must be parenthesized, got {test!r}")
        self.test, self.then, self.orelse = test, then, orelse
        self.family = _families_of([then] + ([orelse] if orelse is not None else []))

    def render(self) -> str:
        body = f"/{self.test}?{self.then.render()}"
        if self.orelse is not None:
            body += f":{self.orelse.render()}"
        return "(" + body + ";)"


_STOP = ",}|):;"


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def expect(self, ch: str) -> None:
        if self.peek() != ch:
            raise GrammarError(f"expected {ch!r} at offset {self.pos} in {self.text!r}")
        self.pos += 1

    def strategy(self, family: str) -> Node:
        terms = []
        while self.peek() and self.peek() not in _STOP:
            ch = self.peek()
            if ch == "(":
                terms.append(self.group(family))
            elif ch == "/":
                terms.append(self.cond(family))
            elif ch.isalpha():
                terms.append(self.method(family))
            else:
                raise GrammarError(f"unexpected {ch!r} at offset {self.pos} in {self.text!r}")
        if not terms:
            return Empty()
        return terms[0] if len(terms) == 1 else Seq(*terms)

    def group(self, family: str) -> Node:
        self.expect("(")
        alts = [self.strategy(family)]
        while self.peek() == "|":
            self.pos += 1
            alts.append(self.strategy(family))
        self.expect(")")
        return alts[0] if len(alts) == 1 else Select(*alts)

    def cond(self, family: str) -> Node:
        self.expect("/")
        if self.peek() != "(":
            raise GrammarError(f"condition test must start with '(' at offset {self.pos}")
        depth, start = 0, self.pos
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            depth += ch == "("
            depth -= ch == ")"
            self.pos += 1
            if depth == 0:
                break
        test = self.text[start : self.pos]
        self.expect("?")
        then = self.strategy(family)
        orelse = None
        if self.peek() == ":":
            self.pos += 1
            orelse = self.strategy(family)
        self.expect(";")
        return Cond(test, then, orelse)

    def method(self, family: str) -> Node:
        letter = self.peek()
        cls = _FAMILY_METHODS[family].get(letter)
        if cls is None:
            raise UnknownMethodError(
                f"no method {letter!r} in PyScotch's {family} table (offset {self.pos}); "
                "if Scotch accepts it, the builder's tables are behind upstream"
            )
        self.pos += 1
        kwargs = {}
        if self.peek() == "{":
            self.pos += 1
            while True:
                start = self.pos
                while self.peek() and (self.peek().isalnum() or self.peek() == "_"):
                    self.pos += 1
                name = self.text[start : self.pos]
                self.expect("=")
                if name in cls.strat_slots:
                    child = self.strategy(cls.strat_slots[name])
                    if isinstance(child, Empty):
                        raise HollowSlotError(f"{cls.__name__} ({family} {letter!r}): strategy slot {name}= is empty")
                    kwargs[name] = child
                elif name in cls.value_params:
                    start = self.pos
                    while self.peek() and self.peek() not in ",}":
                        self.pos += 1
                    token = self.text[start : self.pos]
                    typ = cls.value_params[name]
                    try:
                        kwargs[name] = typ(token) if typ in (int, float) else token
                    except ValueError:
                        raise GrammarError(f"{cls.__name__}: {name}={token!r} is not a {typ.__name__}") from None
                else:
                    raise UnknownParameterError(
                        f"{cls.__name__} ({family} {letter!r}) has no parameter {name!r} in PyScotch's "
                        "table; if Scotch accepts it, the builder's tables are behind upstream"
                    )
                if self.peek() == ",":
                    self.pos += 1
                    continue
                self.expect("}")
                break
        try:
            return cls(**kwargs)
        except TypeError as e:
            if "missing required strategy parameter" in str(e):
                raise HollowSlotError(f"{cls.__name__} ({family} {letter!r}): {e}") from None
            raise


def parse(text: str, family: str) -> Node:
    """Parse a Scotch strategy string into a typed tree under `family`.

    Raises UnknownMethodError / UnknownParameterError when the string uses
    something PyScotch's tables do not model (the signal that upstream moved),
    HollowSlotError when a strategy-valued slot is missing or empty (the
    stratdummy trap, detected from the tables alone — no library call), and
    GrammarError for anything else malformed. The result renders back to a
    plain Scotch string: `parse(s, f).render()` means the same thing to Scotch
    as `s` (the test suite asserts this on every built-in default).
    """
    if family not in _FAMILY_METHODS:
        raise ValueError(f"unknown grammar family {family!r}; one of {sorted(_FAMILY_METHODS)}")
    parser = _Parser(text.strip())
    node = parser.strategy(family)
    if parser.pos != len(parser.text):
        raise GrammarError(f"trailing input at offset {parser.pos} in {text!r}: {parser.text[parser.pos :]!r}")
    return node
