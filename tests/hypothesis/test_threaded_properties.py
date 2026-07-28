"""Property-based tests on graphs large enough to engage Scotch's threads.

The other test tiers dodge parallel nondeterminism: the golden-master pipeline
pins SCOTCH_PTHREAD_NUMBER=1 + SCOTCH_DETERMINISTIC=1 for byte-exact outputs,
and the older hypothesis tests use graphs of at most ~20 vertices — far below
the thresholds where Scotch spawns threads. This suite is the opposite tier:
it deliberately runs with whatever threading the machine provides (nothing is
pinned) on graphs of 256..2300 vertices — sizes where thread scheduling
demonstrably changes results between identical runs — and asserts the
properties that must hold for EVERY schedule:

- every vertex is assigned (no -1), part indices are in range;
- every part is used, and no part exceeds a calibrated balance bound
  (worst observed ratio over 60 threaded runs: 1.012; bound: 1.10 + 1);
- orderings are valid bijective permutations;
- the graph itself survives the operation (check() still passes).

Results are NOT compared across runs — under free threading equality is
explicitly not a contract. Each Hypothesis example repeats the operation a few
times, since every threaded run is a fresh schedule sample even for identical
input.
"""

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pyscotch import Graph
from pyscotch.strategy import Strategies, Strategy

REPEATS = 3  # threaded runs per example: each one samples a new schedule

# =============================================================================
# Fast builders for connected graphs of threading-relevant size (numpy CSR;
# the per-edge generation used in test_graph_properties.py does not scale).
# =============================================================================


def build_grid(width, height):
    """4-neighbour 2D grid graph as (verttab, edgetab)."""
    n = width * height
    degrees = np.full(n, 4, dtype=np.int64)
    xs = np.arange(n) % width
    ys = np.arange(n) // width
    # note: the borders must be summed as integers — `+` on numpy bool arrays
    # is elementwise OR, which would dock corners 1 instead of 2
    for border in (xs == 0, xs == width - 1, ys == 0, ys == height - 1):
        degrees -= border.astype(np.int64)
    verttab = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(degrees, out=verttab[1:])
    edgetab = np.empty(verttab[-1], dtype=np.int64)
    pos = verttab[:-1].copy()
    for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
        nx, ny = xs + dx, ys + dy
        ok = (nx >= 0) & (nx < width) & (ny >= 0) & (ny < height)
        edgetab[pos[ok]] = ny[ok] * width + nx[ok]
        pos[ok] += 1
    return verttab, edgetab


def build_circulant(n, offsets):
    """Circulant graph: v ~ v +/- o for each offset. Connected (offset 1)."""
    offs = np.array(sorted(offsets), dtype=np.int64)
    deltas = np.concatenate([-offs[::-1], offs])
    neighbours = (np.arange(n)[:, None] + deltas[None, :]) % n
    neighbours.sort(axis=1)
    verttab = np.arange(0, n * len(deltas) + 1, len(deltas), dtype=np.int64)
    return verttab, neighbours.reshape(-1).copy()


def make_graph(verttab, edgetab):
    g = Graph()
    g.build(verttab, edgetab)
    assert g.check()
    return g


# =============================================================================
# Builder self-tests. The builders are test *infrastructure*: g.check() only
# validates CSR consistency, so a builder bug that yields a structurally valid
# but wrong-shaped graph would silently weaken every property test below.
# Each builder is therefore diffed against a naive reference implementation.
# =============================================================================


def _naive_grid(width, height):
    n = width * height
    nbrs = [[] for _ in range(n)]
    for y in range(height):
        for x in range(width):
            for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    nbrs[y * width + x].append(ny * width + nx)
    return nbrs


@pytest.mark.parametrize("width,height", [(2, 2), (2, 5), (3, 3), (5, 4), (16, 16), (17, 3)])
def test_build_grid_matches_naive_reference(width, height):
    verttab, edgetab = build_grid(width, height)
    ref = _naive_grid(width, height)
    assert len(verttab) == width * height + 1
    for v, expected in enumerate(ref):
        got = set(edgetab[verttab[v] : verttab[v + 1]].tolist())
        assert got == set(expected), f"vertex {v}: {sorted(got)} != {sorted(expected)}"


def test_build_grid_degree_distribution():
    """Regression for the numpy bool-sum bug: `+` on boolean arrays is OR, so
    corner vertices got degree 3 instead of 2 (each of the two borders they
    sit on must dock one edge — summed as integers, not OR'd)."""
    width, height = 7, 5
    verttab, _ = build_grid(width, height)
    degrees = np.diff(verttab)
    counts = dict(zip(*np.unique(degrees, return_counts=True)))
    assert counts == {
        2: 4,                                       # corners
        3: 2 * (width - 2) + 2 * (height - 2),      # non-corner border
        4: (width - 2) * (height - 2),              # interior
    }, f"degree distribution {counts}"


@pytest.mark.parametrize("n,offsets", [(8, {1}), (9, {1, 3}), (100, {1, 7, 40}), (257, {1, 2})])
def test_build_circulant_matches_naive_reference(n, offsets):
    verttab, edgetab = build_circulant(n, offsets)
    assert np.array_equal(np.diff(verttab), np.full(n, 2 * len(offsets)))
    for v in range(n):
        got = set(edgetab[verttab[v] : verttab[v + 1]].tolist())
        expected = {(v + o) % n for o in offsets} | {(v - o) % n for o in offsets}
        assert got == expected, f"vertex {v}: {sorted(got)} != {sorted(expected)}"


# =============================================================================
# The properties that must hold for every thread schedule
# =============================================================================


def assert_partition_properties(part, nvert, nparts, label):
    assert len(part) == nvert, f"{label}: wrong length"
    unassigned = int((part < 0).sum())
    assert unassigned == 0, f"{label}: {unassigned}/{nvert} vertices unassigned (-1)"
    assert part.max() < nparts, f"{label}: part index out of range"
    counts = np.bincount(part, minlength=nparts)
    assert (counts > 0).all(), f"{label}: empty parts, sizes={counts.tolist()}"
    bound = int(np.ceil(nvert / nparts) * 1.10) + 1
    assert counts.max() <= bound, (
        f"{label}: imbalanced beyond calibrated bound ({counts.max()} > {bound}), "
        f"sizes={counts.tolist()}"
    )


def assert_ordering_properties(permtab, peritab, nvert, label):
    assert np.array_equal(np.sort(permtab), np.arange(nvert)), f"{label}: not a permutation"
    assert np.array_equal(peritab[permtab], np.arange(nvert)), f"{label}: inverse inconsistent"


STRATEGY_FACTORIES = [
    ("default", lambda: None),
    ("quality", Strategies.partition_quality),
    ("fast", Strategies.partition_fast),
]


# =============================================================================
# Hypothesis tier: topology and parameter variety
# =============================================================================


@st.composite
def threaded_grid(draw):
    width = draw(st.integers(min_value=16, max_value=44))
    height = draw(st.integers(min_value=16, max_value=44))
    return width, height


@given(dims=threaded_grid(), nparts=st.integers(2, 8), strat=st.sampled_from(STRATEGY_FACTORIES))
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_grid_partition_properties_under_threads(dims, nparts, strat):
    width, height = dims
    nvert = width * height
    name, factory = strat
    verttab, edgetab = build_grid(width, height)
    for repeat in range(REPEATS):
        g = make_graph(verttab, edgetab)
        part = g.partition(nparts, factory())
        assert_partition_properties(
            part, nvert, nparts, f"grid {width}x{height} nparts={nparts} strat={name} run={repeat}"
        )
        assert g.check(), "partition corrupted the graph"


@given(
    n=st.integers(min_value=256, max_value=1500),
    extra_offsets=st.sets(st.integers(min_value=2, max_value=40), min_size=1, max_size=3),
    nparts=st.integers(2, 6),
)
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_circulant_partition_properties_under_threads(n, extra_offsets, nparts):
    offsets = {1} | {o for o in extra_offsets if o < n // 2}
    verttab, edgetab = build_circulant(n, offsets)
    for repeat in range(REPEATS):
        g = make_graph(verttab, edgetab)
        part = g.partition(nparts)
        assert_partition_properties(
            part, n, nparts, f"circulant n={n} offsets={sorted(offsets)} nparts={nparts} run={repeat}"
        )


@given(dims=threaded_grid())
@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_grid_ordering_properties_under_threads(dims):
    width, height = dims
    nvert = width * height
    verttab, edgetab = build_grid(width, height)
    for repeat in range(REPEATS):
        g = make_graph(verttab, edgetab)
        permtab, peritab = g.order()
        assert_ordering_properties(permtab, peritab, nvert, f"grid {width}x{height} run={repeat}")


# =============================================================================
# Stress tier: one big fixed instance, more repeats, every strategy
# =============================================================================


@pytest.mark.parametrize("strat_name,factory", STRATEGY_FACTORIES)
@pytest.mark.parametrize("nparts", [2, 7])
def test_big_grid_stress(strat_name, factory, nparts):
    """48x48 grid (2304 vertices), well above every threading threshold."""
    verttab, edgetab = build_grid(48, 48)
    for repeat in range(5):
        g = make_graph(verttab, edgetab)
        part = g.partition(nparts, factory())
        assert_partition_properties(
            part, 48 * 48, nparts, f"48x48 nparts={nparts} strat={strat_name} run={repeat}"
        )


def test_big_grid_ordering_actually_reorders():
    """On 2304 vertices the default ordering must never be the identity —
    an identity permutation here means the strategy did no work at all
    (the do-nothing default-strategy bug class, once carried by the
    since-removed set_ordering_default)."""
    verttab, edgetab = build_grid(48, 48)
    for repeat in range(5):
        g = make_graph(verttab, edgetab)
        permtab, peritab = g.order()
        assert_ordering_properties(permtab, peritab, 48 * 48, f"48x48 order run={repeat}")
        assert not np.array_equal(permtab, np.arange(48 * 48)), (
            "default ordering returned the identity permutation on a 48x48 grid"
        )
