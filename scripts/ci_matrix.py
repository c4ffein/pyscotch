#!/usr/bin/env python3
"""Emit the GitHub Actions build matrix from the Scotch catalog.

Single source of truth: pyscotch/scotch_build.py. One matrix entry per
catalogued release, every expectation DERIVED, never hand-typed:

    quickfix        "yes"/"no"  — the version has quickfix patches
    symbol          (quickfix)  — suffixed symbol the patched lib must export
    pristine_grep   (quickfix)  — diagnosis a --pristine build must fail with
    pristine_build  (quickfix)  — which variant (--sequential/--parallel) exhibits it
    repro           "fail-expected" if the version is in _SKIPPED_VERSIONS
                    (known upstream nondeterminism), else "pass"
    behavioral      "yes" when the version has behavioral patches (CI rebuilds
                    with --auto-allow-behavioral-patches and re-runs the harness)

    --full   the scotch-build.yml matrix (all fields)
    --pypi   the pypi-verify.yml matrix (scotch + quickfix only)

Output is a JSON object {"include": [...]} for `fromJSON` in the workflow.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyscotch.scotch_build import (  # noqa: E402  (path insert above)
    _BEHAVIORAL_PATCHES,
    _KNOWN_VERSIONS,
    _PATCH_VERIFY,
    _PATCHES,
    _SKIPPED_VERSIONS,
    _version_key,
)


def matrix(full: bool) -> dict:
    rows = []
    for version in sorted(_KNOWN_VERSIONS, key=_version_key, reverse=True):
        row = {"scotch": version, "quickfix": "yes" if _PATCHES.get(version) else "no"}
        if full:
            row.update(_PATCH_VERIFY.get(version, {}))
            row["repro"] = "fail-expected" if version in _SKIPPED_VERSIONS else "pass"
            if _BEHAVIORAL_PATCHES.get(version):
                row["behavioral"] = "yes"
        rows.append(row)
    return {"include": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--full", action="store_true", help="scotch-build.yml matrix")
    g.add_argument("--pypi", action="store_true", help="pypi-verify.yml matrix")
    args = ap.parse_args(argv)
    print(json.dumps(matrix(full=args.full), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
