"""Differential tests: PyScotch versus Scotch's own reference tools.

The strongest honesty check available — the oracle is upstream's own CLI
binary driving the very same library: `gpart` for partitioning, `gord` for
ordering, `gmap` for mapping onto a target architecture. Under deterministic
settings (fixed seed build, one thread, deterministic algorithms) PyScotch's
output for a graph is BYTE-IDENTICAL to the reference tool's — mapping/ordering
file included. Established empirically on 7.0.12 (gpart) / 7.0.13 (gord, gmap);
any divergence here means PyScotch stopped driving the library the way the
reference implementation does — a finding, never noise.

Requires the reference binaries built from the same Scotch version and flags
as the loaded library. Point PYSCOTCH_GPART / PYSCOTCH_GORD / PYSCOTCH_GMAP at
them (and make sure their libscotch is resolvable, e.g. via LD_LIBRARY_PATH);
each test skips when its binary is absent. CI wires this via `make build-reference-tools`
+ `make test-differential` in the test workflow (locally: same two targets).
First run of the partition tier found a real bug: save_mapping wrote 0-based
labels for based graphs, where gpart preserves the graph's base.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pyscotch import Architecture, Graph, random_reset

REPO = Path(__file__).resolve().parent.parent.parent

BASED_GRAPH = REPO / "external" / "scotch" / "src" / "check" / "data" / "m16x16_b100000_v.grf"
TGT_DIR = REPO / "external" / "scotch" / "tgt"  # shipped target architectures (submodule)

DETERMINISTIC_ENV = {
    **os.environ,
    "SCOTCH_PTHREAD_NUMBER": "1",
    "SCOTCH_DETERMINISTIC": "1",
}


def _reference_tool(envvar, name):
    exe = os.environ.get(envvar) or shutil.which(name)
    if not exe:
        pytest.skip(f"no {name} binary (set {envvar} to enable differential tests)")
    probe = subprocess.run([exe, "-V"], env=DETERMINISTIC_ENV, capture_output=True)
    if probe.returncode != 0:
        pytest.skip(f"{name} at {exe} not runnable (check LD_LIBRARY_PATH)")
    return exe


def _gpart():
    return _reference_tool("PYSCOTCH_GPART", "gpart")


def _gord():
    return _reference_tool("PYSCOTCH_GORD", "gord")


def _gmap():
    return _reference_tool("PYSCOTCH_GMAP", "gmap")


@pytest.fixture(autouse=True)
def deterministic_process(monkeypatch):
    """The comparison needs the deterministic knobs in THIS process too —
    but the library read them at import; skip if the env disagrees."""
    if os.environ.get("SCOTCH_PTHREAD_NUMBER") != "1":
        pytest.skip(
            "differential byte-comparison requires SCOTCH_PTHREAD_NUMBER=1 "
            "(and SCOTCH_DETERMINISTIC=1) set before the test session starts"
        )


def run_gpart(nparts, graph_file, out):
    """`gpart <nparts> <graph.grf> <out.map>` — partition into nparts parts."""
    subprocess.run(
        [_gpart(), str(nparts), str(graph_file), str(out)],
        env=DETERMINISTIC_ENV,
        check=True,
        capture_output=True,
    )


def run_gord(graph_file, out):
    """`gord <graph.grf> <out.ord>` — order for sparse-matrix factorization."""
    subprocess.run(
        [_gord(), str(graph_file), str(out)],
        env=DETERMINISTIC_ENV,
        check=True,
        capture_output=True,
    )


def run_gmap(graph_file, tgt_file, out):
    """`gmap <graph.grf> <arch.tgt> <out.map>` — map onto a target architecture."""
    subprocess.run(
        [_gmap(), str(graph_file), str(tgt_file), str(out)],
        env=DETERMINISTIC_ENV,
        check=True,
        capture_output=True,
    )


class TestPartitionMatchesGpart:
    """Partitioning: `gpart <nparts> <in> <out>` versus ``Graph.partition(n)``
    + ``save_mapping()``. gpart maps the graph onto a complete graph of
    ``nparts`` vertices (``SCOTCH_archCmplt``) — which is exactly what
    ``partition()`` builds — loads with baseval=-1 and vertex+edge weights,
    and, given no ``-s``, runs the default strategy that ``partition(n)`` also
    uses; both write via SCOTCH_graphMapSave. So the mapping files are
    byte-identical. The recipe to reproduce `gpart` from the API is therefore
    ``g.load(f); g.save_mapping(out, g.partition(n))`` under the deterministic
    settings this module sets (plus ``random_reset()`` for the from-seed state
    a fresh gpart process starts in).
    """

    def test_base0_graph_byte_identical(self, tmp_path):
        """ring.grf (base 0, no weights): the plain case — labels start at 0."""
        graph_file = REPO / "tests" / "golden" / "ring.grf"
        theirs = tmp_path / "gpart.map"
        ours = tmp_path / "pyscotch.map"
        run_gpart(2, graph_file, theirs)

        g = Graph()
        g.load(graph_file)
        random_reset()  # gpart runs fresh-process: compare from the seed state
        g.save_mapping(ours, g.partition(2))
        assert ours.read_bytes() == theirs.read_bytes(), (
            "pyscotch and gpart disagree on a base-0 graph — PyScotch no "
            "longer drives the library like the reference tool"
        )

    def test_based_graph_byte_identical(self, tmp_path):
        """Base-100000 graph: requires load(baseval=-1) to preserve the file's
        base, and save_mapping's base-aware labels (the bug this tier caught)."""
        graph_file = REPO / "external" / "scotch" / "src" / "check" / "data" / "m16x16_b100000_v.grf"
        if not graph_file.exists():
            pytest.skip("scotch submodule data not initialized")
        theirs = tmp_path / "gpart.map"
        ours = tmp_path / "pyscotch.map"
        run_gpart(4, graph_file, theirs)

        g = Graph()
        g.load(graph_file, baseval=-1)
        random_reset()
        g.save_mapping(ours, g.partition(4))
        assert ours.read_bytes() == theirs.read_bytes()

    def test_rebased_load_same_assignment(self, tmp_path):
        """The default load (rebase to 0) must still compute the SAME
        partition as gpart — only the vertex labels in the file differ."""
        graph_file = REPO / "external" / "scotch" / "src" / "check" / "data" / "m16x16_b100000_v.grf"
        if not graph_file.exists():
            pytest.skip("scotch submodule data not initialized")
        theirs = tmp_path / "gpart.map"
        run_gpart(4, graph_file, theirs)
        tokens = theirs.read_text().split()
        their_assign = [int(p) for _, p in zip(*[iter(tokens[1:])] * 2)]

        g = Graph()
        g.load(graph_file)  # default: rebased to 0
        random_reset()
        ours = g.partition(4)
        assert ours.tolist() == their_assign


class TestOrderingMatchesGord:
    """Same honesty check for ordering: `gord <in> <out>` versus
    ``Graph.order()`` + ``order_save()``. gord loads with baseval=-1 (preserve
    the file's base) and vertex weights, and — given no ``-c``/``-o`` — runs the
    default ordering strategy, exactly what ``order(strategy=None)`` does; both
    write via SCOTCH_graphOrderSave. So the ordering files are byte-identical.
    """

    def test_base0_graph_byte_identical(self, tmp_path):
        """ring.grf (base 0): recipe is
        ``perm, peri = g.order(); g.order_save(out, perm, peri)``."""
        graph_file = REPO / "tests" / "golden" / "ring.grf"
        theirs = tmp_path / "gord.ord"
        ours = tmp_path / "pyscotch.ord"
        run_gord(graph_file, theirs)

        g = Graph()
        g.load(graph_file)
        random_reset()  # gord runs fresh-process: compare from the seed state
        perm, peri = g.order()
        g.order_save(ours, perm, peri)
        assert ours.read_bytes() == theirs.read_bytes(), (
            "pyscotch and gord disagree on a base-0 graph — PyScotch no "
            "longer drives the library like the reference tool"
        )

    def test_based_graph_byte_identical(self, tmp_path):
        """Base-100000 graph: requires load(baseval=-1) to preserve the file's
        base, like gord's own SCOTCH_graphLoad(..., -1, 2)."""
        graph_file = BASED_GRAPH
        if not graph_file.exists():
            pytest.skip("scotch submodule data not initialized")
        theirs = tmp_path / "gord.ord"
        ours = tmp_path / "pyscotch.ord"
        run_gord(graph_file, theirs)

        g = Graph()
        g.load(graph_file, baseval=-1)
        random_reset()
        perm, peri = g.order()
        g.order_save(ours, perm, peri)
        assert ours.read_bytes() == theirs.read_bytes()


class TestMappingMatchesGmap:
    """Mapping onto an arbitrary target architecture: `gmap <in> <tgt> <out>`
    versus ``Graph.map(arch)`` + ``map_save()``. Partitioning is mapping onto a
    complete graph; this exercises the general case (hypercube, mesh, …) against
    a shipped .tgt file. gmap loads with vertex+edge weights and — given no
    ``-s`` — runs the default strategy, exactly what ``map(strategy=None)`` does;
    both write via SCOTCH_graphMapSave, so the mapping files are byte-identical.
    """

    def test_base0_graph_onto_hypercube(self, tmp_path):
        graph_file = REPO / "tests" / "golden" / "ring.grf"
        tgt_file = TGT_DIR / "h3.tgt"  # hypercube of dimension 3 (8 terminals)
        if not tgt_file.exists():
            pytest.skip("scotch submodule tgt/ not initialized")
        theirs = tmp_path / "gmap.map"
        ours = tmp_path / "pyscotch.map"
        run_gmap(graph_file, tgt_file, theirs)

        g = Graph()
        g.load(graph_file)
        arch = Architecture()
        arch.load(tgt_file)
        random_reset()  # gmap runs fresh-process: compare from the seed state
        g.map_save(ours, g.map(arch), arch)
        assert ours.read_bytes() == theirs.read_bytes(), (
            "pyscotch and gmap disagree on a base-0 graph — PyScotch no "
            "longer drives the library like the reference tool"
        )

    def test_based_graph_onto_mesh(self, tmp_path):
        """Base-100000 graph onto a 2D mesh: base-aware labels (like gpart) plus
        an arbitrary non-complete architecture."""
        graph_file = BASED_GRAPH
        tgt_file = TGT_DIR / "m5x5.tgt"  # 5x5 mesh (25 terminals)
        if not graph_file.exists() or not tgt_file.exists():
            pytest.skip("scotch submodule data/ or tgt/ not initialized")
        theirs = tmp_path / "gmap.map"
        ours = tmp_path / "pyscotch.map"
        run_gmap(graph_file, tgt_file, theirs)

        g = Graph()
        g.load(graph_file, baseval=-1)
        arch = Architecture()
        arch.load(tgt_file)
        random_reset()
        g.map_save(ours, g.map(arch), arch)
        assert ours.read_bytes() == theirs.read_bytes()
