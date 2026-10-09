"""Act 1 — the sequential API: NumPy in, NumPy out."""

import os

# Reproducibility needs deterministic EXECUTION, not just the fixed seed:
# without this, thread scheduling makes identical PRNG states yield different
# partitions. Runtime switch since Scotch 7.0 — no rebuild needed.
os.environ.setdefault("SCOTCH_DETERMINISTIC", "1")

from pyscotch import Graph, Mapping, random_reset, scotch_version

print("Loaded Scotch", ".".join(map(str, scotch_version())))

# A 16x16 grid: the friendliest possible partitioning target.
n = 16
edges = []
for r in range(n):
    for c in range(n):
        v = r * n + c
        if c < n - 1:
            edges.append((v, v + 1))
        if r < n - 1:
            edges.append((v, v + n))

g = Graph.from_edges(edges)
g.save("grid.grf")  # the CLI part of the demo reuses this file
vertnbr, edgenbr = g.size()
print(f"grid: {vertnbr} vertices, {edgenbr} edges -> grid.grf")


def cut(parts):
    """Edges whose endpoints land in different parts — what you pay in MPI."""
    return int(sum(parts[u] != parts[v] for u, v in edges))


parts = g.partition(4)
m = Mapping(parts)
print(f"partition(4): sizes={m.get_partition_sizes().tolist()}, balance={m.balance():.2f}, cut={cut(parts)}")

perm, iperm = g.order()  # fill-reducing nested-dissection ordering
print(f"order(): permutation of {len(perm)} vertices")

# Reproducibility, Scotch's way: nothing resets the PRNG implicitly — the
# same explicit call a C program makes (SCOTCH_randomReset).
random_reset()
a = g.partition(4)
random_reset()
b = g.partition(4)
print("random_reset() -> identical partitions:", bool((a == b).all()))

# And the stream left running is a feature, not a bug: exploration. (On the
# regular grid every try finds the optimal cut — so use an irregular graph,
# where each try lands in a different local optimum.)
import random  # noqa: E402  (narrative script: imports where the story needs them)

rng = random.Random(42)
irregular = list({tuple(sorted(rng.sample(range(vertnbr), 2))) for _ in range(3 * vertnbr)})
ig = Graph.from_edges(irregular)


def icut(parts):
    return int(sum(parts[u] != parts[v] for u, v in irregular))


cuts = sorted(icut(ig.partition(4)) for _ in range(10))
print(f"irregular graph, 10 running-stream tries: cuts {cuts[0]}..{cuts[-1]}")
print(f"  keep the best -> {cuts[0]} ({100 * (cuts[-1] - cuts[0]) / cuts[-1]:.0f}% better than the worst)")
