"""Stamp pyscotch/_version.py from a release tag — used by CI before building.

Usage:
    python scripts/apply_release_version.py <ref>

<ref> is a git ref or tag, e.g. "v7.0.0", "v7.0.0rc1", or the full
"refs/tags/v7.0.0" (GitHub's github.ref). The leading "refs/.../" and "v" are
stripped, the remainder is validated as a PEP 440 release/pre-release version,
and pyscotch/_version.py is rewritten to match.

It is a deliberate NO-OP (exit 0) when <ref> is not a release version tag — a
branch name like "main", a "-dev" tag, etc. — so the same call is safe to run
unconditionally on every build, tagged or not.
"""

import re
import sys
from pathlib import Path

# PEP 440 final or pre-release: X.Y.Z, optionally aN / bN / rcN. Deliberately
# strict: no local/dev/post segments reach a published release this way.
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?$")
_VERSION_LINE_RE = re.compile(r'^__version__ = "[^"]*"$', re.MULTILINE)


def main(argv):
    ref = (argv[1] if len(argv) > 1 else "").strip()
    tag = ref.rsplit("/", 1)[-1]  # refs/tags/v7.0.0 -> v7.0.0
    version = tag[1:] if tag.startswith("v") else tag

    if not _VERSION_RE.match(version):
        print(
            f"apply_release_version: '{ref}' is not a release version tag; "
            "leaving pyscotch/_version.py unchanged"
        )
        return 0

    path = Path(__file__).resolve().parent.parent / "pyscotch" / "_version.py"
    text = path.read_text()
    new_text, n = _VERSION_LINE_RE.subn(f'__version__ = "{version}"', text)
    if n != 1:
        print(
            f"apply_release_version: expected exactly one __version__ line in "
            f"{path}, found {n}",
            file=sys.stderr,
        )
        return 1
    path.write_text(new_text)
    print(f"apply_release_version: set __version__ = {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
