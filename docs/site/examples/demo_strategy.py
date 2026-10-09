"""Act 2 — strategy strings, validated by the library's own parsers."""

from pyscotch import Graph, Strategy
from pyscotch.strategy_grammar import Bipart, Mapping, Seq

# In C, SCOTCH_stratGraphMap(&strat, "m") parses successfully — and silently
# builds a do-nothing multilevel: every strategy-valued slot defaults to
# stratdummy, so partitioning puts every vertex in one part. PyScotch probes
# each string with the library's own parsers (all three sequential grammars)
# and detects hollow slots via SCOTCH_stratSave round-trips:
for bad in ("m", "r{job=t,map=t,poli=S,bal=0.05}", "garbage{"):
    try:
        Strategy(bad)
        print(f"UNEXPECTED: {bad!r} accepted")
    except ValueError as e:
        print(f"Strategy({bad!r:34}) refused: {str(e).splitlines()[0]}")

print()

# The typed builder makes the trap unrepresentable: strategy-valued slots are
# REQUIRED constructor arguments, and str(tree) is a plain Scotch grammar
# string — Scotch stays the sole semantic authority.
tree = Mapping.Multilevel(
    low=Mapping.Recursive(sep=Seq(Bipart.Gg(), Bipart.Fm())),
    asc=Mapping.Fm(move=120),
)
print("typed tree renders to plain grammar :", tree)
print("canonical form (SCOTCH_stratSave)   :", tree.validate())

# The same 16x16 grid demo_api.py partitions (self-contained here).
n = 16
edges = [(r * n + c, r * n + c + 1) for r in range(n) for c in range(n - 1)]
edges += [(r * n + c, (r + 1) * n + c) for r in range(n - 1) for c in range(n)]
g = Graph.from_edges(edges)

parts = g.partition(4, Strategy(str(tree)))
print("partitioned the grid with it, parts :", sorted(set(parts.tolist())))
