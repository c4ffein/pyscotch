"""
On-disk store for user-built Scotch libraries (`pyscotch scotch build`).

Pure path/bookkeeping logic — no Scotch, numpy, or heavy imports — so
libscotch.py can consult it during discovery without a cycle.

Layout (default root ~/.local/share/pyscotch, override with PYSCOTCH_HOME):

    <home>/
      builds/
        7.0.11-64-par/          # one dir per build key "<version>-<bits>-<seq|par>"
          lib64/                # the .so files, mirroring scotch-builds/lib{32,64}
        7.0.12-64-seq/
          lib64/
      current                   # text file: the default build key, or absent
      cache/                    # downloaded source tarballs

A build key is "<version>-<bits>-<variant>", e.g. "7.0.11-64-par".
"""

import os
import re
from pathlib import Path

_KEY_RE = re.compile(r"^(?P<version>\d+\.\d+\.\d+)-(?P<bits>32|64)-(?P<variant>seq|par)$")


def home() -> Path:
    """Root of the PyScotch data store."""
    env = os.environ.get("PYSCOTCH_HOME")
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "pyscotch"


def builds_dir() -> Path:
    return home() / "builds"


def cache_dir() -> Path:
    return home() / "cache"


def make_key(version: str, bits: int, parallel: bool) -> str:
    return f"{version}-{bits}-{'par' if parallel else 'seq'}"


def parse_key(key: str):
    """Return {'version','bits','variant','parallel'} or None if malformed."""
    m = _KEY_RE.match(key)
    if not m:
        return None
    return {
        "version": m.group("version"),
        "bits": int(m.group("bits")),
        "variant": m.group("variant"),
        "parallel": m.group("variant") == "par",
    }


def build_dir(key: str) -> Path:
    return builds_dir() / key


def build_lib_dir(key: str) -> Path:
    info = parse_key(key)
    bits = info["bits"] if info else 64
    return build_dir(key) / f"lib{bits}"


def _current_file() -> Path:
    return home() / "current"


def get_default_key():
    """The build key marked as default, or None (also None if it's gone)."""
    f = _current_file()
    if not f.is_file():
        return None
    key = f.read_text().strip()
    return key if key and build_dir(key).is_dir() else None


def set_default_key(key: str) -> None:
    home().mkdir(parents=True, exist_ok=True)
    _current_file().write_text(key + "\n")


def clear_default() -> None:
    _current_file().unlink(missing_ok=True)


def list_keys():
    """Sorted list of installed build keys."""
    d = builds_dir()
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and parse_key(p.name))


def _patches_file(key: str) -> Path:
    return build_dir(key) / "PATCHES"


def write_patches(key: str, names) -> None:
    """Record which bundled patches were applied when building `key`."""
    if names:
        _patches_file(key).write_text("\n".join(names) + "\n")


def read_patches(key: str):
    """Names of patches applied to this build (empty list if pristine)."""
    f = _patches_file(key)
    return f.read_text().split() if f.is_file() else []


def has_lib(key: str, parallel: bool) -> bool:
    """True if this build actually contains the libraries it needs."""
    libd = build_lib_dir(key)
    if not (libd / "libscotch.so").exists():
        return False
    if parallel and not (libd / "libptscotch.so").exists():
        return False
    return True


def managed_lib_dir(bits: int, parallel: bool):
    """Lib dir of the default build if it satisfies (bits, parallel), else None.

    Used as a discovery tier in libscotch.py: a build the user explicitly
    `use`d takes precedence over the bundled wheel libraries. Falls through
    (returns None) when no default is set or the default cannot serve the
    requested integer width / parallel variant.
    """
    key = get_default_key()
    if key is None:
        return None
    info = parse_key(key)
    if info is None or info["bits"] != bits:
        return None
    if not has_lib(key, parallel):
        return None
    return build_lib_dir(key)
