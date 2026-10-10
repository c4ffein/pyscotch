"""Import a strategy Scotch wrote, tweak it typed, hand it back."""

from pyscotch import Graph, Strategy
from pyscotch.strategy_grammar import MAPPING, Bipart, HollowSlotError, Mapping, Seq, UnknownParameterError, parse

# Any Scotch strategy string parses into a typed tree — here the canonical
# form Scotch itself produces for a builder tree (validate() returns it).
canonical = Mapping.Multilevel(
    low=Mapping.Recursive(sep=Seq(Bipart.Gg(), Bipart.Fm())),
    asc=Mapping.Fm(move=120),
).validate()
print("Scotch's canonical form:", canonical)

tree = parse(canonical, MAPPING)
assert isinstance(tree, Mapping.Ml)

# Parsing is table-driven: the tree knows which parameters are strategies
# (children) and which are values, so tweaks are typed, not string surgery.
tree._children["asc"]._values["move"] = 300  # deeper FM refinement on the way up
tweaked = tree.render()
assert "move=300" in tweaked

edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3), (2, 4), (4, 5), (5, 3)]
parts = Graph.from_edges(edges).partition(nparts=2, strategy=Strategy(tweaked))
print("partitioned with the tweaked import:", parts.tolist())

# What parse() refuses — from the tables alone, no library call:
for bad, err in (("m", HollowSlotError), ("m{low=f,asc=f,foo=1}", UnknownParameterError)):
    try:
        parse(bad, MAPPING)
        raise AssertionError("unreachable")
    except err as e:
        print(f"parse({bad!r}) -> {type(e).__name__}")
