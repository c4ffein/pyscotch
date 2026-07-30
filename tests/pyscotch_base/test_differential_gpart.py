"""Differential tests: PyScotch versus Scotch's own reference tools.

The strongest honesty check available — the oracle is upstream's `gpart`
binary driving the very same library. Under deterministic settings (fixed
seed build, one thread, deterministic algorithms) PyScotch's partition of a
graph is BYTE-IDENTICAL to gpart's, mapping file included. Established
empirically on 7.0.12; any divergence here means PyScotch stopped driving the
library the way the reference implementation does — a finding, never noise.

Requires a gpart binary built from the same Scotch version and flags as the
loaded library. Point PYSCOTCH_GPART at it (and make sure its libscotch is
resolvable, e.g. via LD_LIBRARY_PATH); the tests skip when it is absent —
CI wires this via the golden-master toolchain. First run of this tier found
a real bug: save_mapping wrote 0-based labels for based graphs, where gpart
preserves the graph's base.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pyscotch import Graph, random_reset

REPO = Path(__file__).resolve().parent.parent.parent

DETERMINISTIC_ENV = {
    **os.environ,
    "SCOTCH_PTHREAD_NUMBER": "1",
    "SCOTCH_DETERMINISTIC": "1",
}


def _gpart():
    exe = os.environ.get("PYSCOTCH_GPART") or shutil.which("gpart")
    if not exe:
        pytest.skip("no gpart binary (set PYSCOTCH_GPART to enable differential tests)")
    probe = subprocess.run([exe, "-V"], env=DETERMINISTIC_ENV, capture_output=True)
    if probe.returncode != 0:
        pytest.skip(f"gpart at {exe} not runnable (check LD_LIBRARY_PATH)")
    return exe


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
    subprocess.run(
        [_gpart(), str(nparts), str(graph_file), str(out)],
        env=DETERMINISTIC_ENV,
        check=True,
        capture_output=True,
    )


class TestPartitionMatchesGpart:
    def test_base0_graph_byte_identical(self, tmp_path):
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
