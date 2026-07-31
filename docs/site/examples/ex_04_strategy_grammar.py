"""Compose a strategy with the typed grammar builder instead of a raw string."""
from pyscotch import Graph, Mapping as MappingResult, Strategy
from pyscotch.strategy_grammar import Bipart, Mapping, Seq

# A multilevel mapping strategy: recursive bipartitioning at the coarsest
# level (graph-growing then Fiduccia-Mattheyses), FM refinement on the way up.
tree = Mapping.Multilevel(
    low=Mapping.Recursive(sep=Seq(Bipart.Gg(), Bipart.Fm())),
    asc=Mapping.Fm(move=120),
)

# str(tree) is a PLAIN Scotch strategy string — no new semantics.
assert str(tree) == "m{asc=f{move=120},low=r{sep=hf}}", str(tree)

# Strategy-valued slots are REQUIRED arguments: a hollow (do-nothing) slot is
# unrepresentable in the builder, where a hand-written string degenerates
# silently in C Scotch.
try:
    Mapping.Multilevel(asc=Mapping.Fm())  # forgot low=
    raise AssertionError("unreachable")
except TypeError:
    pass

# Hand-written strings get the same safety at construction since 7.0.1:
try:
    Strategy("m")  # parses in C Scotch, but every slot is a do-nothing dummy
    raise AssertionError("unreachable")
except ValueError:
    pass

# validate() parses the tree with the live library and returns the canonical
# (SCOTCH_stratSave) form.
assert tree.validate()

# And it is just a string, so it plugs into the normal API:
edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3), (2, 4), (4, 5), (5, 3)]
graph = Graph.from_edges(edges)
parts = graph.partition(nparts=2, strategy=Strategy(str(tree)))
assert MappingResult(parts).num_partitions() == 2
print(f"partitioned with {tree!r}: {parts.tolist()}")
