#!/usr/bin/env python3
"""Golden-master pipeline for the PyScotch sdist user journey.

Runs the full walkthrough documented in TEMOP/RECIPE.md — install PyScotch from
the sdist into a clean venv with NO Scotch anywhere, watch every step fail with
the documented error, build Scotch through the CLI, watch everything work, then
the same for the parallel variant — and compares every user-visible output
byte-for-byte against the golden files committed in tests/golden/.

The failures are first-class outputs: a stage whose exit code or error text
drifts from the golden is a regression, exactly like a wrong partition.

Usage:
    python scripts/golden_walkthrough.py            # verify against goldens
    python scripts/golden_walkthrough.py --update   # (re)generate goldens
    python scripts/golden_walkthrough.py --keep     # keep the workdir around

Requires: an sdist in dist/ (python -m build --sdist), a C toolchain with
flex >= 2.6.4 / bison / zlib headers, and OpenMPI + mpirun for the parallel
stages. Network access to gitlab.inria.fr (sha256-pinned download).

Normalization: only things the environment forces to vary are rewritten before
comparison — the workdir path, the platform line, and the Python/mpi4py version
numbers. Everything PyScotch itself prints is compared verbatim; if goldens
generated on one machine fail on another, that divergence is a finding, not
noise (regenerate from the CI artifact if CI is the reference).
"""

import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "golden"
RING = GOLDEN / "ring.grf"
HELLO = REPO / "examples" / "hello_pyscotch.py"

# ---------------------------------------------------------------------------
# Helper scripts the walkthrough drives (written into the workdir verbatim).
# ---------------------------------------------------------------------------
API_DEMO = """\
import numpy as np
from pyscotch import Graph, random_reset, scotch_version

print("scotch version:", ".".join(map(str, scotch_version())))
g = Graph()
g.build(np.array([0, 2, 4, 6, 8, 10, 12]), np.array([1, 5, 0, 2, 1, 3, 2, 4, 3, 5, 4, 0]))
print("partition(2):", g.partition(2).tolist())
random_reset()  # order() is a thin binding: reset explicitly for reproducible output
perm, peri = g.order()
print("order perm :", perm.tolist())
print("order valid:", bool((peri[perm] == np.arange(6)).all()))
"""

EXPECT_NO_PTSCOTCH = """\
try:
    from pyscotch import Dgraph  # noqa: F401
    print("UNEXPECTED: import succeeded")
except FileNotFoundError as e:
    print("FileNotFoundError:", e)
"""

DGRAPH_NO_INIT = """\
from pyscotch import Dgraph

try:
    Dgraph()
    print("UNEXPECTED: Dgraph constructed")
except RuntimeError as e:
    print("RuntimeError:", e)
"""


def normalize(text: str, work: Path) -> str:
    """Rewrite the environment-dependent parts of an output for comparison."""
    for p in {str(work), str(work.resolve())}:
        text = text.replace(p, "<WORK>")
    text = re.sub(r"(?m)^(  Platform\s+).*$", r"\g<1><PLATFORM>", text)
    text = re.sub(r"(?m)^(  Python\s+)\d+\.\d+\.\d+\S*$", r"\g<1><PYTHON>", text)
    text = re.sub(r"(?m)^(  mpi4py\s+)\d+\.\d+(\.\d+)?\S*$", r"\g<1><MPI4PY>", text)
    text = re.sub(r"(?m)^(  MPI library\s+).*$", r"\g<1><MPILIB>", text)
    return text


class Runner:
    def __init__(self, work: Path, update: bool):
        self.work = work
        self.update = update
        self.store = work / "store"
        self.venv = work / "venv"
        self.failures = []
        self._stage_no = 0

    # -- environment ---------------------------------------------------------
    def base_env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYSCOTCH_")}
        env["PYSCOTCH_HOME"] = str(self.store)
        env["PATH"] = f"{self.venv / 'bin'}{os.pathsep}{env.get('PATH', '')}"
        # Byte-exact comparison requires deterministic execution, which needs
        # BOTH knobs (verified empirically):
        # - SCOTCH_PTHREAD_NUMBER=1: thread scheduling is result-affecting, and
        #   the 1-thread path is the only one stable on any core count (with
        #   SCOTCH_DETERMINISTIC=1, >=2 threads agree with each other but NOT
        #   with 1 thread — a 1-core runner would drift).
        # - SCOTCH_DETERMINISTIC=1: PT-Scotch receives point-to-point messages
        #   first-come-first-serve otherwise, making mpirun stages
        #   nondeterministic regardless of threads (3 identical runs on a 12^3
        #   grid gave 3 different partitions). Runtime env var, Scotch >= 7.0.
        # Today's tiny graphs mostly dodge both effects — by luck, not design.
        env["SCOTCH_PTHREAD_NUMBER"] = "1"
        env["SCOTCH_DETERMINISTIC"] = "1"
        env.update(extra)
        return env

    def setup(self, sdist: Path):
        """Create the venv and install the sdist + numpy (output not goldened)."""
        uv = shutil.which("uv")
        if uv:
            subprocess.run([uv, "venv", str(self.venv)], check=True, capture_output=True)
        else:
            subprocess.run([sys.executable, "-m", "venv", str(self.venv)], check=True)
        self.pip_install(str(sdist), "numpy", no_binary="pyscotch")
        for name, body in [
            ("api_demo.py", API_DEMO),
            ("expect_no_ptscotch.py", EXPECT_NO_PTSCOTCH),
            ("dgraph_no_init.py", DGRAPH_NO_INIT),
        ]:
            (self.work / name).write_text(body)
        shutil.copy(RING, self.work / "ring.grf")
        shutil.copy(HELLO, self.work / "hello_pyscotch.py")

    def pip_install(self, *pkgs, no_binary=None):
        py = self.venv / "bin" / "python"
        uv = shutil.which("uv")
        if uv:
            cmd = [uv, "pip", "install", "--python", str(py)]
        else:
            cmd = [str(py), "-m", "pip", "install", "-q"]
        if no_binary:
            cmd += ["--no-binary", no_binary]
        subprocess.run(cmd + list(pkgs), check=True, capture_output=True)

    # -- stages --------------------------------------------------------------
    def stage(self, name, argv, rc, env=None, stdout_only=False, files=(), timeout=600):
        """Run one stage; compare its output (and produced files) to goldens."""
        self._stage_no += 1
        label = f"{self._stage_no:02d}-{name}"
        print(f"--- {label}: {' '.join(argv)}", flush=True)
        proc = subprocess.run(
            argv,
            cwd=self.work,
            env=self.base_env(**(env or {})),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if stdout_only else subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != rc:
            print(proc.stdout)
            sys.exit(f"{label}: exit code {proc.returncode}, expected {rc} — aborting")
        self._compare(f"{label}.txt", normalize(proc.stdout, self.work))
        for produced, golden_name in files:
            data = (self.work / produced).read_text()
            self._compare(golden_name, normalize(data, self.work))

    def _compare(self, golden_name, actual):
        golden_path = GOLDEN / golden_name
        if self.update:
            golden_path.write_text(actual)
            print(f"    wrote {golden_path.relative_to(REPO)}")
            return
        expected = golden_path.read_text() if golden_path.exists() else None
        if expected is None:
            self.failures.append(f"{golden_name}: golden file missing (run with --update)")
            return
        if actual != expected:
            diff = "".join(
                difflib.unified_diff(
                    expected.splitlines(keepends=True),
                    actual.splitlines(keepends=True),
                    fromfile=f"golden/{golden_name}",
                    tofile="actual",
                )
            )
            self.failures.append(f"{golden_name}: output drifted\n{diff}")
            (self.work / f"actual-{golden_name}").write_text(actual)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update", action="store_true", help="regenerate the golden files")
    ap.add_argument("--keep", action="store_true", help="keep the workdir for inspection")
    args = ap.parse_args()

    sdists = sorted((REPO / "dist").glob("pyscotch-*.tar.gz"))
    if not sdists:
        sys.exit("No sdist found in dist/ — run `python -m build --sdist` first.")
    sdist = sdists[-1]
    print(f"sdist: {sdist.name}")
    # A stale sdist silently validates OLD code — the walkthrough tests the
    # tarball, not the working tree. Refuse rather than prove the wrong thing.
    newest_src = max(
        p.stat().st_mtime
        for p in (REPO / "pyscotch").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    if sdist.stat().st_mtime < newest_src:
        sys.exit(
            f"{sdist.name} is older than the newest file under pyscotch/ — "
            "rebuild it first (`python -m build --sdist`) so the walkthrough "
            "tests the code you just changed."
        )

    work = Path(tempfile.mkdtemp(prefix="pyscotch-golden-"))
    print(f"workdir: {work}")
    r = Runner(work, update=args.update)
    try:
        r.setup(sdist)
        py = str(r.venv / "bin" / "python")
        cli = str(r.venv / "bin" / "pyscotch")
        par = {"PYSCOTCH_PARALLEL": "1"}

        # -- sequential journey ------------------------------------------------
        r.stage("doctor-empty", [cli, "doctor"], rc=1)
        r.stage("partition-no-scotch", [cli, "partition", "ring.grf", "-n", "2"], rc=1)
        r.stage("build-seq", [cli, "scotch", "build", "7.0.11", "--sequential", "--use"], rc=0)
        r.stage("doctor-seq", [cli, "doctor"], rc=0)
        r.stage(
            "partition-ok",
            [cli, "partition", "ring.grf", "-n", "2", "-o", "ring.part"],
            rc=0,
            files=[("ring.part", "ring.part.golden")],
        )
        r.stage(
            "order-ok",
            [cli, "order", "ring.grf", "-o", "ring.ord"],
            rc=0,
            files=[("ring.ord", "ring.ord.golden")],
        )
        r.stage("python-api", [py, "api_demo.py"], rc=0)

        # -- the documented failure modes on the way to parallel ---------------
        r.stage("import-ptscotch-missing", [py, "expect_no_ptscotch.py"], rc=0, env=par)
        r.stage("doctor-parallel-missing", [cli, "doctor"], rc=1, env=par)

        # -- parallel journey --------------------------------------------------
        r.pip_install("mpi4py")
        r.stage("build-par", [cli, "scotch", "build", "7.0.11", "--parallel", "--use"], rc=0)
        r.stage("scotch-list", [cli, "scotch", "list"], rc=0)
        mpirun = shutil.which("mpirun")
        if mpirun is None:
            sys.exit("mpirun not found — the parallel stages need OpenMPI installed.")
        r.stage(
            "hello-mpirun",
            [mpirun, "--oversubscribe", "-n", "2", py, "hello_pyscotch.py"],
            rc=0,
            env={**par, "PYSCOTCH_INT_SIZE": "64", "PYSCOTCH_MPI_OVERSUBSCRIBE": "1"},
            stdout_only=True,  # per-rank stderr banners interleave nondeterministically
        )
        r.stage("dgraph-no-mpi-init", [py, "dgraph_no_init.py"], rc=0, env=par)
        r.stage("doctor-parallel-ok", [cli, "doctor"], rc=0, env=par)
    finally:
        if args.keep or r.failures:
            print(f"workdir kept: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)

    if r.failures:
        print("\n" + "=" * 70)
        for f in r.failures:
            print(f"FAILED {f}")
        sys.exit(f"{len(r.failures)} golden comparison(s) failed")
    print("\nAll stages matched the golden outputs." if not args.update else "\nGoldens updated.")


if __name__ == "__main__":
    main()
