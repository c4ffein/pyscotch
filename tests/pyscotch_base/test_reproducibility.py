"""Reproducibility stress harness: run the SAME operation N times in fresh
processes under deterministic settings and assert exactly one distinct result.

Single-shot tests cannot catch flaky nondeterminism (thread scheduling); this
tier makes it a hard assertion. It exists because of a real regression: the
test_random_proc ~1/5 flake on Scotch 7.0.16 turned out to be upstream commit
7a934a8 making bgraphBipartGg() multi-threaded with scheduling-dependent
worker PRNG seeds (see QUESTIONS_FOR_SCOTCH_TEAM.md, 2026-10-08) — exactly
what an N-run distinct-count would have caught on bump day.

Opt-in via PYSCOTCH_REPRO=1 (`make test-reproducibility`); runs per config via
PYSCOTCH_REPRO_RUNS (default 12). Point PYSCOTCH_LIB_DIR at the library to
audit. A FAILURE here is a true statement about that library: pristine 7.0.16
fails (the regression), 7.0.13–7.0.15 and a 7.0.16 built with the bundled
behavioral determinism patch pass.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("PYSCOTCH_REPRO") != "1",
    reason="reproducibility stress harness is opt-in: set PYSCOTCH_REPRO=1",
)

REPO = Path(__file__).resolve().parent.parent.parent
# Default: the submodule's copy; PYSCOTCH_REPRO_GRAPH overrides (CI checkouts
# without the submodule extract it from the cached source tarball instead).
GRAPH = Path(
    os.environ.get(
        "PYSCOTCH_REPRO_GRAPH",
        REPO / "external" / "scotch" / "src" / "check" / "data" / "m16x16_b100000_v.grf",
    )
)
RUNS = int(os.environ.get("PYSCOTCH_REPRO_RUNS", "12"))

# The known-sensitive spot: a strategy reaching bgraphBipartGg (`h`), the
# method whose 7.0.16 threading broke determinism. The default strategy is
# also affected (it reaches `h` through the FM no-frontier fallback).
H_STRATEGY = "r{job=t,map=t,poli=S,sep=m{vert=120,low=h{pass=20},asc=f{bal=0.01,move=120}}}"

SEQ_CHILD = """\
import os
from pyscotch import Graph, Strategy
g = Graph()
g.load(os.environ["PYSCOTCH_REPRO_GRAPH"], baseval=-1)
s = os.environ.get("PYSCOTCH_REPRO_STRAT") or None
parts = g.partition(4, Strategy(s) if s else None)
print(",".join(map(str, parts.tolist())))
"""

DGRAPH_CHILD = """\
from mpi4py import MPI
from pyscotch import Dgraph
comm = MPI.COMM_WORLD
dg = Dgraph(comm=comm)
dg.build_grid_3d(8, 8, 8)
part = dg.part(4)
gathered = comm.gather(part.tolist(), root=0)
dg.exit()
if comm.Get_rank() == 0:
    print(",".join(str(x) for ranks in gathered for x in ranks))
"""


def _graph_or_skip():
    if not GRAPH.exists():
        pytest.skip("scotch submodule data not initialized")
    return GRAPH


def _run_fresh(threads, strategy=None, runs=RUNS):
    """Partition in `runs` FRESH processes; return the set of result strings.

    Fresh process = PRNG at the fixed seed, like gpart and like every real
    one-shot user; what varies between runs is only scheduling — which is
    the thing under test.
    """
    env = {
        **os.environ,
        "SCOTCH_DETERMINISTIC": "1",
        "SCOTCH_PTHREAD_NUMBER": str(threads),
        "PYSCOTCH_PARALLEL": "0",
        "PYSCOTCH_REPRO_GRAPH": str(_graph_or_skip()),
        "PYSCOTCH_REPRO_STRAT": strategy or "",
    }
    results = set()
    for _ in range(runs):
        proc = subprocess.run([sys.executable, "-c", SEQ_CHILD], env=env, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        results.add(proc.stdout.strip().splitlines()[-1])
    return results


class TestSequentialReproducibility:
    def test_default_strategy_two_threads(self):
        results = _run_fresh(threads=2)
        assert len(results) == 1, (
            f"{len(results)} distinct partitions over {RUNS} deterministic runs "
            "(2 threads) — the loaded Scotch is not reproducible"
        )

    def test_thread_count_does_not_matter_above_one(self):
        """Documented upstream contract: with >= 2 threads the deterministic
        result is the same whatever the thread count."""
        two = _run_fresh(threads=2)
        four = _run_fresh(threads=4)
        assert len(two) == 1 and len(four) == 1
        assert two == four, "2-thread and 4-thread deterministic results differ"

    def test_single_thread(self):
        """1 thread is a separate code path (may differ from >=2) but must
        agree with itself."""
        assert len(_run_fresh(threads=1)) == 1

    def test_h_strategy_four_threads(self):
        """The strategy naming `h` outright — the 7.0.16 regression's
        epicenter."""
        assert len(_run_fresh(threads=4, strategy=H_STRATEGY)) == 1, (
            "bgraphBipartGg (`h`) is not deterministic under threads — "
            "see the 7.0.16 entry in QUESTIONS_FOR_SCOTCH_TEAM.md"
        )


class TestParallelReproducibility:
    def test_dgraph_part_under_mpirun(self):
        mpirun = shutil.which("mpirun")
        if not mpirun:
            pytest.skip("no mpirun")
        env = {
            **os.environ,
            "SCOTCH_DETERMINISTIC": "1",
            "PYSCOTCH_PARALLEL": "1",
        }
        probe = subprocess.run(
            [sys.executable, "-c", "import mpi4py; import pyscotch"],
            env=env,
            capture_output=True,
            text=True,
        )
        if probe.returncode != 0:
            pytest.skip(f"parallel stack unavailable: {probe.stderr.strip().splitlines()[-1]}")
        results = set()
        for _ in range(max(RUNS // 2, 4)):
            proc = subprocess.run(
                [mpirun, "--oversubscribe", "-n", "2", sys.executable, "-c", DGRAPH_CHILD],
                env=env,
                capture_output=True,
                text=True,
            )
            assert proc.returncode == 0, proc.stdout + proc.stderr
            results.add(proc.stdout.strip().splitlines()[-1])
        assert len(results) == 1, (
            f"{len(results)} distinct Dgraph partitions across identical deterministic mpirun runs"
        )
