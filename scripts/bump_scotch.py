#!/usr/bin/env python3
"""Gated Scotch version bump: `make bump SCOTCH=7.0.17 [BUMP_FLAGS=--apply]`.

The bump is a CHECK first and a mechanical edit second. Stages 1-4 modify
nothing and stop at the first failure with a classified report — the script
never decides a policy question (skip the release? bind a new function?); it
hands you the facts and the exact next step:

  1. download   fetch the GitLab archive, compute its sha256
  2. compile    `pyscotch scotch build` (64-bit, parallel) into a temp store
                -> a failure here means a QUICKFIX is needed (diagnosis shown)
  3. gate       the reproducibility harness against that build
                -> a failure here is an upstream nondeterminism: decide between
                   `_SKIPPED_VERSIONS` (keep the pin) and investigating
  4. surface    exported SCOTCH_* symbols vs the currently shipped library, and
                the API-completeness tests against the new one
                -> new symbols = upstream added functions: bind them (or record
                   them as known-unbound in the completeness test)

With --apply, after all four pass:

  5. edit       catalog entry + _SHIPPED_VERSION in pyscotch/scotch_build.py,
                submodule checkout (inside external/scotch only — the
                superproject's index is never touched)
  6. regenerate make clean-scotch + make docs-api, the manuals page map, a
                fresh sdist, goldens (--update); then `git diff --stat`

Left to you afterwards: read the diff, write the CHANGELOG entry, retire any
`_SKIPPED_VERSIONS` / behavioral-patch entry the new release supersedes.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pyscotch import scotch_build as sb  # noqa: E402  (lazy import: loads no Scotch)

PY = sys.executable
CATALOG_FILE = REPO / "pyscotch" / "scotch_build.py"


def stage(n, title):
    print(f"\n=== [{n}/6] {title}")


def fail(code, what, next_step, detail=""):
    print(f"\nSTOP ({what}).")
    if detail:
        print(detail.rstrip())
    print(f"\nNext step: {next_step}")
    sys.exit(code)


def run(cmd, env=None, cwd=None, check=False):
    proc = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd))} failed:\n{proc.stdout}{proc.stderr}")
    return proc


# --- stage 1 ---------------------------------------------------------------
def download(version, workdir):
    url = sb._GITLAB.format(v=version)
    dest = workdir / f"scotch-v{version}.tar.gz"
    print(f"  {url}")
    try:
        with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:  # noqa: BLE001 - reported, not handled
        fail(1, "download failed", f"check that v{version} exists on gitlab.inria.fr", str(e))
    sha = hashlib.sha256(dest.read_bytes()).hexdigest()
    pinned = sb._KNOWN_VERSIONS.get(version)
    if pinned and pinned != sha:
        fail(
            1,
            "checksum drift",
            "GitLab regenerated the archive: investigate before trusting it",
            f"  pinned {pinned}\n  got    {sha}",
        )
    print(f"  sha256 {sha}{'  (matches the catalog pin)' if pinned else '  (new to the catalog)'}")
    return url, sha


# --- stage 2 ---------------------------------------------------------------
def compile_candidate(version, url, sha, home):
    env = {**os.environ, "PYSCOTCH_HOME": str(home)}
    cmd = [PY, "-m", "pyscotch.cli", "scotch", "build", version, "--parallel", "--url", url, "--sha256", sha]
    proc = run(cmd, env=env, cwd=REPO)
    out = proc.stdout + proc.stderr
    if proc.returncode != 0:
        hint = sb._diagnose_make_output(out)
        fail(
            2,
            "compile failed",
            "this release needs a QUICKFIX: write the patch, add it to _PATCHES (+ _PATCH_VERIFY), and re-run",
            (hint + "\n" if hint else "") + out[-3000:],
        )
    libdir = home / "builds" / f"{version}-64-par" / "lib64"
    tag = "  (quickfix applied)" if "Applied quickfix" in out else ""
    print(f"  built {libdir}{tag}")
    return libdir


# --- stage 3 ---------------------------------------------------------------
def gate_reproducibility(libdir, runs):
    env = {
        **os.environ,
        "PYSCOTCH_REPRO": "1",
        "PYSCOTCH_REPRO_RUNS": str(runs),
        "PYSCOTCH_INT_SIZE": "64",
        "PYSCOTCH_PARALLEL": "0",
        "PYSCOTCH_LIB_DIR": str(libdir),
        "PYSCOTCH_MPI_OVERSUBSCRIBE": "1",
    }
    # Only the stress classes: the module's vendored-graph tripwire may skip
    # without the submodule, and a skip here is treated as a failure.
    proc = run(
        [
            PY,
            "-m",
            "pytest",
            "tests/pyscotch_base/test_reproducibility.py",
            "-q",
            "-rs",
            "-k",
            "TestSequentialReproducibility or TestParallelReproducibility",
        ],
        env=env,
        cwd=REPO,
    )
    output = proc.stdout + proc.stderr
    tail = "\n".join(output.strip().splitlines()[-15:])
    if proc.returncode != 0:
        fail(
            3,
            "reproducibility gate failed",
            "upstream nondeterminism — DECIDE: add the version to "
            "_SKIPPED_VERSIONS with the reason (pin stays), or investigate/patch; do not bump blindly",
            tail,
        )
    if re.search(r"\b\d+ skipped\b", output):
        # An opted-in audit that could not run is not a pass.
        fail(
            3,
            "reproducibility gate could not run fully (tests skipped)",
            "a skipped leg is not a pass: fix the environment (graph file, mpirun, mpi4py) and re-run",
            tail,
        )
    print("  " + tail.splitlines()[-1])


# --- stage 4 ---------------------------------------------------------------
def exported_symbols(libdir):
    syms = set()
    # Core libraries only: the dev build also ships the libscotchmetis /
    # libptscotchparmetis shims, which a `scotch build` store build does not.
    for so in sorted(p for p in libdir.glob("lib*.so") if p.name in ("libscotch.so", "libptscotch.so")):
        out = run(["nm", "-D", "--defined-only", str(so)]).stdout
        for line in out.splitlines():
            name = line.split()[-1]
            if name.startswith("SCOTCH_"):
                syms.add(re.sub(r"_(32|64)$", "", name))
    return syms


def surface_drift(new_libdir, old_libdir):
    new, old = exported_symbols(new_libdir), exported_symbols(old_libdir) if old_libdir else set()
    added, removed = sorted(new - old), sorted(old - new)
    if old_libdir:
        print(f"  exported SCOTCH_* symbols: {len(new)} (shipped build: {len(old)})")
        for s in added:
            print(f"    + {s}")
        for s in removed:
            print(f"    - {s}")
    env = {**os.environ, "PYSCOTCH_INT_SIZE": "64", "PYSCOTCH_PARALLEL": "1", "PYSCOTCH_LIB_DIR": str(new_libdir)}
    proc = run([PY, "-m", "pytest", "tests/pyscotch_base/test_api_completeness.py", "-q"], env=env, cwd=REPO)
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-12:])
    if proc.returncode != 0 or added:
        what = "API surface drift" if added else "API-completeness tests failed"
        fail(
            4,
            what,
            "upstream added/changed public functions: bind them in libscotch.py (+ the high-level "
            "class, docs example, make docs-api), or record them as known-unbound in test_api_completeness.py",
            ("new symbols: " + ", ".join(added) + "\n" if added else "") + tail,
        )
    print(
        "  " + tail.splitlines()[-1] + ("" if not removed else f"  (note: {len(removed)} symbol(s) removed upstream)")
    )


# --- stages 5-6 ------------------------------------------------------------
def edit_catalog(version, sha):
    text = CATALOG_FILE.read_text()
    if version not in sb._KNOWN_VERSIONS:
        text = re.sub(r"(_KNOWN_VERSIONS = \{\n)", rf'\1    "{version}": "{sha}",\n', text, count=1)
    text = re.sub(r'_SHIPPED_VERSION = "[^"]+"', f'_SHIPPED_VERSION = "{version}"', text, count=1)
    CATALOG_FILE.write_text(text)
    print(f"  catalog: pinned {version}, _SHIPPED_VERSION = {version}")


def move_submodule(version):
    sub = REPO / "external" / "scotch"
    run(["git", "-C", str(sub), "fetch", "--tags", "-q"], check=True)
    run(["git", "-C", str(sub), "checkout", "-q", f"v{version}"], check=True)
    print(f"  submodule external/scotch -> v{version} (superproject index untouched)")


def regenerate():
    run(["make", "clean-scotch"], cwd=REPO, check=True)
    print("  make docs-api (rebuilds 64-bit from the submodule, regenerates api_data.json) ...")
    run(["make", "docs-api"], cwd=REPO, check=True)
    print("  manuals page map ...")
    run([PY, "docs/site/gen_pdf_map.py"], cwd=REPO, check=True)
    print("  sdist (from outside the repo root) ...")
    with tempfile.TemporaryDirectory() as td:
        run(["uv", "build", "--sdist", "--project", str(REPO)], cwd=td, check=True)
    print("  goldens --update ...")
    run([PY, "scripts/golden_walkthrough.py", "--update"], cwd=REPO, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version", help="Scotch release to bump to, e.g. 7.0.17")
    ap.add_argument("--apply", action="store_true", help="after the checks pass, perform the bump")
    ap.add_argument("--runs", type=int, default=12, help="reproducibility runs per config (default 12)")
    args = ap.parse_args(argv)
    version = args.version
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        ap.error("version must look like 7.0.17")
    if version == sb.shipped_version():
        print(f"{version} is already the shipped release; nothing to do.")
        return 0
    old_libdir = REPO / "scotch-builds" / "lib64"
    old_libdir = old_libdir if (old_libdir / "libscotch.so").exists() else None

    with tempfile.TemporaryDirectory(prefix="pyscotch-bump-") as td:
        work = Path(td)
        stage(1, f"download Scotch {version}")
        url, sha = download(version, work)
        stage(2, "compile (64-bit, parallel) into a temporary store")
        libdir = compile_candidate(version, url, sha, work / "home")
        stage(3, f"reproducibility gate ({args.runs} fresh runs per config)")
        gate_reproducibility(libdir, args.runs)
        stage(4, "API surface vs the shipped build + completeness tests")
        surface_drift(libdir, old_libdir)

        if not args.apply:
            print(f"\nAll checks passed for Scotch {version}. Re-run with --apply to perform the bump.")
            return 0
        stage(5, "edit catalog / shipped pin / submodule")
        edit_catalog(version, sha)
        move_submodule(version)
        stage(6, "regenerate derived artifacts")
        regenerate()
    print("\n" + run(["git", "diff", "--stat"], cwd=REPO).stdout)
    print(
        "Done. Review the diff, write the CHANGELOG entry, and retire any _SKIPPED_VERSIONS /\n"
        "behavioral-patch entry this release supersedes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
