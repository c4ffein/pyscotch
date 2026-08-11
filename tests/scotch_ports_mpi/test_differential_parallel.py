"""Parallel differential tests: PyScotch versus PT-Scotch's own CLI tools.

The distributed counterpart of tests/pyscotch_base/test_differential.py. The
oracle is upstream's `dgpart` / `dgord` binary run under mpirun; PyScotch runs
the matching Dgraph call sequence under mpirun from a standalone script
(mpi_scripts/differential_dg*.py). Under deterministic settings
(SCOTCH_DETERMINISTIC=1, one thread) the centralized mapping/ordering file the
root process writes is BYTE-IDENTICAL between the two — proven empirically on
7.0.13, np=2. Any divergence means PyScotch stopped driving PT-Scotch the way
the reference tool does — a finding, never noise.

Both sides must load the *same* PT-Scotch (version, flags, int size). This tier
therefore pins the 32-bit parallel variant, matching the stock-flag reference
binaries `make build-reference-tools` builds. Wiring (all set by `make test-differential`):

- PYSCOTCH_DGPART / PYSCOTCH_DGORD: the reference binaries (their libptscotch
  is resolved from the binary's own directory).
- PYSCOTCH_PAR_LIB_DIR: the suffixed PyScotch parallel libs (scotch-builds/lib32
  from `make build-all`) the child scripts load via PYSCOTCH_LIB_DIR.
- PYSCOTCH_PAR_INT_SIZE (default "32"): int size for the child scripts.
- PYSCOTCH_MPI_OVERSUBSCRIBE=1: add --oversubscribe (shared CI runners).

Each test skips when its binary, the parallel lib dir, or mpirun is absent.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
MPI_SCRIPTS = Path(__file__).resolve().parent / "mpi_scripts"
BASED_GRAPH = REPO / "external" / "scotch" / "src" / "check" / "data" / "m16x16_b100000_v.grf"
RING_GRAPH = REPO / "tests" / "golden" / "ring.grf"

PAR_LIB_DIR = os.environ.get("PYSCOTCH_PAR_LIB_DIR")
PAR_INT_SIZE = os.environ.get("PYSCOTCH_PAR_INT_SIZE", "32")

DETERMINISTIC = {"SCOTCH_PTHREAD_NUMBER": "1", "SCOTCH_DETERMINISTIC": "1"}


def _mpirun_prefix(nprocs):
    exe = shutil.which("mpirun")
    if not exe:
        pytest.skip("no mpirun on PATH")
    cmd = [exe]
    if os.environ.get("PYSCOTCH_MPI_OVERSUBSCRIBE") == "1":
        cmd.append("--oversubscribe")
    return cmd + ["-np", str(nprocs)]


def _reference(envvar, name):
    exe = os.environ.get(envvar) or shutil.which(name)
    if not exe:
        pytest.skip(f"no {name} binary (set {envvar} to enable parallel differential tests)")
    return exe


def _ref_env(binpath):
    """Environment for a reference binary: deterministic knobs + its own
    libptscotch (copied next to it by `make build-reference-tools`)."""
    libdir = str(Path(binpath).resolve().parent)
    return {
        **os.environ,
        **DETERMINISTIC,
        "LD_LIBRARY_PATH": libdir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""),
    }


def _child_env():
    """Environment for the PyScotch MPI child: the 32-bit parallel variant,
    loaded from the suffixed dev libraries."""
    if not PAR_LIB_DIR or not Path(PAR_LIB_DIR).exists():
        pytest.skip("set PYSCOTCH_PAR_LIB_DIR to the PyScotch parallel lib dir (e.g. scotch-builds/lib32)")
    return {
        **os.environ,
        **DETERMINISTIC,
        "PYSCOTCH_INT_SIZE": PAR_INT_SIZE,
        "PYSCOTCH_PARALLEL": "1",
        "PYSCOTCH_LIB_DIR": PAR_LIB_DIR,
        "LD_LIBRARY_PATH": PAR_LIB_DIR + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""),
    }


def _run(cmd, env):
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


class TestDistributedPartitionMatchesDgpart:
    """Distributed partitioning: `mpirun -np N dgpart <nparts> <in> <out>`
    versus, under the same mpirun, ``Dgraph.load(); Dgraph.map_save(complete
    arch)`` (mpi_scripts/differential_dgpart.py). The recipe to reproduce
    `dgpart` from the distributed API is that script — note it calls
    ``random_proc(rank)`` first, as dgpart does; without that per-rank seeding
    the result diverges for non-trivial graphs (see the module docstring).
    """

    @pytest.mark.parametrize("graph", [RING_GRAPH, BASED_GRAPH], ids=["ring", "m16x16_based"])
    def test_byte_identical(self, graph, tmp_path):
        if not graph.exists():
            pytest.skip(f"{graph.name} not available (submodule not initialized?)")
        dgpart = _reference("PYSCOTCH_DGPART", "dgpart")
        child_env = _child_env()  # resolves/skips before doing work
        theirs = tmp_path / "dgpart.map"
        ours = tmp_path / "pyscotch.map"

        _run(_mpirun_prefix(2) + [dgpart, "4", str(graph), str(theirs)], _ref_env(dgpart))
        _run(
            _mpirun_prefix(2)
            + [sys.executable, str(MPI_SCRIPTS / "differential_dgpart.py"), str(graph), str(ours), "4"],
            child_env,
        )
        assert ours.read_bytes() == theirs.read_bytes(), (
            "pyscotch and dgpart disagree — PyScotch no longer drives PT-Scotch "
            "like the reference tool"
        )


class TestDistributedOrderingMatchesDgord:
    """Distributed ordering: `mpirun -np N dgord <in> <out>` versus, under the
    same mpirun, ``Dgraph.load(); order_init/compute; order_save()``
    (mpi_scripts/differential_dgord.py). Same ``random_proc(rank)`` caveat as
    dgpart — it is the tools' first PRNG action and drives the distributed
    candidate election.
    """

    @pytest.mark.parametrize("graph", [RING_GRAPH, BASED_GRAPH], ids=["ring", "m16x16_based"])
    def test_byte_identical(self, graph, tmp_path):
        if not graph.exists():
            pytest.skip(f"{graph.name} not available (submodule not initialized?)")
        dgord = _reference("PYSCOTCH_DGORD", "dgord")
        child_env = _child_env()
        theirs = tmp_path / "dgord.ord"
        ours = tmp_path / "pyscotch.ord"

        _run(_mpirun_prefix(2) + [dgord, str(graph), str(theirs)], _ref_env(dgord))
        _run(
            _mpirun_prefix(2)
            + [sys.executable, str(MPI_SCRIPTS / "differential_dgord.py"), str(graph), str(ours)],
            child_env,
        )
        assert ours.read_bytes() == theirs.read_bytes(), (
            "pyscotch and dgord disagree — PyScotch no longer drives PT-Scotch "
            "like the reference tool"
        )
