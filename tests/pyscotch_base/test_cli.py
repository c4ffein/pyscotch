"""End-to-end tests for the `pyscotch` command-line interface.

The CLI had *no* test coverage at all, which is how it shipped writing `-1`
(unassigned) for every vertex: the API-level tests all went through
`graph.partition(n)` with no strategy, while the CLI passes an explicit
strategy object — a path nothing exercised.

These drive the real entry point in a subprocess (`python -m pyscotch.cli`) and
assert on the *files it produces*, not just its exit code. Anything that only
checks "it didn't crash" is what let the bug through in the first place.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# A 6-vertex ring, in Scotch's .grf format:
#   line 1: version
#   line 2: <vertnbr> <edgenbr>
#   line 3: <baseval> <flagval>
#   then one line per vertex: <degree> <neighbour>...
RING_GRF = """0
6\t12
0\t000
2\t1\t5
2\t0\t2
2\t1\t3
2\t2\t4
2\t3\t5
2\t4\t0
"""

# Every -s choice must produce a real partition. "recursive" used to pass the
# bare Scotch method code "r" — an incomplete strategy that put every vertex
# in one part; it now builds via SCOTCH_stratGraphMapBuild. "multilevel" is a
# documented synonym of "default" (Scotch's default IS multilevel; the
# Strategy.set_multilevel() method was removed outright).
CLI_STRATEGIES = [
    "default",
    "quality",
    "fast",
    "multilevel",
    "recursive",
]


def run_cli(*args, cwd=None, env=None):
    """Invoke the real CLI entry point in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "pyscotch.cli", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def parse_part_file(path: Path):
    """Read a Scotch mapping file -> {vertex: part}. Format: count, then pairs."""
    lines = [ln for ln in path.read_text().split("\n") if ln.strip()]
    count = int(lines[0])
    mapping = {}
    for ln in lines[1:]:
        vertex, part = ln.split()
        mapping[int(vertex)] = int(part)
    assert len(mapping) == count, f"header says {count} vertices, file has {len(mapping)}"
    return mapping


def assert_real_partition(mapping, nparts, nvert):
    """The assertions that actually matter for a partition.

    `max(part) < nparts` alone is NOT enough: an all -1 (unassigned) result
    satisfies it trivially. That exact gap hid a total CLI failure, so the
    lower bound is asserted first and loudly.
    """
    assert len(mapping) == nvert
    unassigned = sorted(v for v, p in mapping.items() if p < 0)
    assert not unassigned, (
        f"{len(unassigned)}/{nvert} vertices left unassigned (-1) — "
        f"the partitioner produced nothing: {unassigned[:10]}"
    )
    assert max(mapping.values()) < nparts, "part index >= nparts"
    used = set(mapping.values())
    assert used == set(range(nparts)), f"expected every part 0..{nparts - 1} to be used, got {used}"


@pytest.fixture
def ring(tmp_path):
    p = tmp_path / "ring.grf"
    p.write_text(RING_GRF)
    return p


class TestCliInfoAndCheck:
    def test_info_reports_size(self, ring):
        r = run_cli("info", str(ring))
        assert r.returncode == 0, r.stderr
        assert "6" in r.stdout and "12" in r.stdout

    def test_check_accepts_valid_graph(self, ring):
        r = run_cli("check", str(ring))
        assert r.returncode == 0, r.stderr
        assert "valid" in r.stdout.lower()


class TestCliPartition:
    def test_partition_writes_a_real_partition(self, ring, tmp_path):
        """The regression: this wrote -1 for every vertex and still exited 0."""
        out = tmp_path / "ring.part"
        r = run_cli("partition", str(ring), "-n", "2", "-o", str(out))
        assert r.returncode == 0, r.stderr
        assert out.exists(), "no partition file written"
        assert_real_partition(parse_part_file(out), nparts=2, nvert=6)

    @pytest.mark.parametrize("nparts", [2, 3])
    def test_partition_nparts(self, ring, tmp_path, nparts):
        out = tmp_path / f"ring.part{nparts}"
        r = run_cli("partition", str(ring), "-n", str(nparts), "-o", str(out))
        assert r.returncode == 0, r.stderr
        assert_real_partition(parse_part_file(out), nparts=nparts, nvert=6)

    def test_partition_default_output_path(self, ring):
        """With no -o, the CLI documents <input>.part.<nparts>."""
        r = run_cli("partition", str(ring), "-n", "2")
        assert r.returncode == 0, r.stderr
        expected = Path(str(ring) + ".part.2")
        assert expected.exists(), f"expected default output at {expected}"
        assert_real_partition(parse_part_file(expected), nparts=2, nvert=6)

    def test_partition_reports_balance(self, ring, tmp_path):
        """A ring split in two must be perfectly balanced (3/3)."""
        out = tmp_path / "ring.part"
        r = run_cli("partition", str(ring), "-n", "2", "-o", str(out))
        assert r.returncode == 0, r.stderr
        sizes = list(parse_part_file(out).values())
        assert sizes.count(0) == 3 and sizes.count(1) == 3, f"unbalanced: {sizes}"

    @pytest.mark.parametrize("strategy", CLI_STRATEGIES)
    def test_every_advertised_strategy_partitions(self, ring, tmp_path, strategy):
        """Every choice offered by `-s` must produce a usable partition.

        If `--help` lists it, it has to work; otherwise we are shipping options
        that silently produce garbage.
        """
        out = tmp_path / f"ring.{strategy}.part"
        r = run_cli("partition", str(ring), "-n", "2", "-s", strategy, "-o", str(out))
        assert r.returncode == 0, r.stderr
        assert_real_partition(parse_part_file(out), nparts=2, nvert=6)


def parse_ord_file(path: Path, nvert):
    """Read an Ordering.save file -> (perm, invp) lists; validate structure.

    Format: count, then one `<vertex> <perm> <invp>` line per vertex.
    """
    lines = [ln for ln in path.read_text().split("\n") if ln.strip()]
    assert int(lines[0]) == nvert, f"header says {lines[0]} vertices, expected {nvert}"
    perm, invp = [-1] * nvert, [-1] * nvert
    for ln in lines[1:]:
        vertex, p, i = (int(x) for x in ln.split())
        perm[vertex], invp[vertex] = p, i
    return perm, invp


def assert_real_ordering(perm, invp, nvert):
    """perm must be a bijection and invp its inverse — not e.g. all zeros."""
    assert sorted(perm) == list(range(nvert)), f"not a permutation: {perm}"
    assert all(invp[perm[v]] == v for v in range(nvert)), "invp is not the inverse of perm"


class TestCliOrder:
    def test_order_writes_a_permutation(self, ring, tmp_path):
        out = tmp_path / "ring.ord"
        r = run_cli("order", str(ring), "-o", str(out))
        assert r.returncode == 0, r.stderr
        assert out.exists(), "no ordering file written"
        text = out.read_text().split()
        assert text, "ordering file is empty"

    @pytest.mark.parametrize("strategy", ["default", "quality", "fast", "nested"])
    def test_every_advertised_order_strategy_works(self, ring, tmp_path, strategy):
        """Every `-s` choice of `order` must produce a real permutation.

        quality/fast used to be silently identical to default (their flag
        constants were None); both now build real strategies via
        SCOTCH_stratGraphOrderBuild. "nested" is a documented synonym of
        "default" (Scotch's default ordering IS nested-dissection based; it
        used to pass the bare "n" string, which returned the identity).
        """
        out = tmp_path / f"ring.{strategy}.ord"
        r = run_cli("order", str(ring), "-s", strategy, "-o", str(out))
        assert r.returncode == 0, r.stderr
        perm, invp = parse_ord_file(out, nvert=6)
        assert_real_ordering(perm, invp, nvert=6)


class TestCliErrorHandling:
    def test_missing_input_file_fails_cleanly(self, tmp_path):
        r = run_cli("partition", str(tmp_path / "nope.grf"), "-n", "2")
        assert r.returncode != 0
        assert "Traceback" not in r.stderr, "a CLI must not dump a traceback by default"
        assert "Error:" in r.stderr

    def test_traceback_available_on_request(self, tmp_path):
        import os

        env = {**os.environ, "PYSCOTCH_TRACEBACK": "1"}
        r = run_cli("partition", str(tmp_path / "nope.grf"), "-n", "2", env=env)
        assert r.returncode != 0
        assert "Traceback" in r.stderr, "PYSCOTCH_TRACEBACK=1 must restore the traceback"

    def test_no_command_prints_help(self):
        r = run_cli()
        assert r.returncode == 1
        assert "usage" in (r.stdout + r.stderr).lower()

    def test_unknown_command_is_rejected(self):
        r = run_cli("frobnicate")
        assert r.returncode != 0


class TestCliDoctor:
    def test_doctor_runs_and_reports(self):
        r = run_cli("doctor")
        # 0 = healthy, 1 = problems found; both are valid, a crash is not.
        assert r.returncode in (0, 1), r.stderr
        assert "PyScotch environment report" in r.stdout

    def test_doctor_json_is_parseable(self):
        import json

        r = run_cli("doctor", "--json")
        assert r.returncode in (0, 1), r.stderr
        payload = json.loads(r.stdout)
        assert "backend" in payload and "problems" in payload


class TestCliScotchStore:
    def test_scotch_list_runs(self):
        r = run_cli("scotch", "list")
        assert r.returncode == 0, r.stderr

    def test_scotch_patches_lists_known_quickfix(self):
        r = run_cli("scotch", "patches")
        assert r.returncode == 0, r.stderr
        assert "7.0.12" in r.stdout
