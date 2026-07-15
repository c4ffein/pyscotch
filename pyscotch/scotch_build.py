"""
`pyscotch scotch` — download, compile, and manage Scotch libraries locally.

A wheel/sdist install has no Scotch source tree, so this builds one from a
pinned upstream release: preflight the toolchain, fetch + checksum the source,
compile the sequential (and optionally parallel) libraries with the
_32/_64-suffixed symbols PyScotch expects, and stage them into the on-disk
store (see _store.py). Builds live side by side; `use` marks a default that
discovery then prefers over the bundled wheel libraries.

Design notes:
  - Preflight FIRST, and hard-stop with a consolidated, distro-aware fix list
    before touching the network or a compiler — no half-built state.
  - Every external step (download, extract, make) captures output and, on
    failure, prints a focused diagnosis (recognising the common Scotch build
    traps) instead of a raw traceback.
  - Checksums are pinned but overridable (--sha256) because GitLab archive
    tarballs are not guaranteed byte-stable forever.
"""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from . import _store

# ---------------------------------------------------------------------------
# Known upstream releases (GitLab archive tarballs). Checksums recorded
# 2026-07-15; override with --sha256 for other versions/patches or if GitLab
# regenerates an archive. --url overrides the source entirely.
# ---------------------------------------------------------------------------
_GITLAB = "https://gitlab.inria.fr/scotch/scotch/-/archive/v{v}/scotch-v{v}.tar.gz"
_KNOWN_VERSIONS = {
    "7.0.12": "870bf681e7e40b6b01c3890dbe7b27da2617660f1722541919a865a6729dcbf2",
    "7.0.11": "ce1ea6e16ca36ae91426a360f639c8f575fccebc0116fbcb381f164c5e862768",
    "7.0.10": "8327725a08cdd4fc7575e291251883b4f93f75b07a54bc58f89f50dcbba7b244",
}
_DEFAULT_VERSION = "7.0.11"

# Base CFLAGS mirror patches/Makefile.inc.default (the flags PyScotch's own
# builds use). Per-build we append -DINTSIZE64 / -DSCOTCH_NAME_SUFFIX / RENAME.
_BASE_CFLAGS = (
    "-O3 -fPIC -U_FORTIFY_SOURCE -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD "
    "-DCOMMON_PTHREAD_AFFINITY_LINUX -DCOMMON_RANDOM_FIXED_SEED "
    "-DSCOTCH_MPI_ASYNC_COLL -DSCOTCH_PTHREAD -DSCOTCH_PTHREAD_MPI -DSCOTCH_RENAME"
)


def _makefile_inc(cc: str, mpicc: str) -> str:
    """Render a Scotch Makefile.inc using the detected compilers."""
    return "\n".join(
        [
            "EXE        =",
            "LIB        = .so",
            "OBJ        = .o",
            "MAKE        = make",
            f"AR        = {cc}",
            "ARFLAGS        = -shared -o",
            "CAT        = cat",
            f"CCS        = {cc}",
            f"CCP        = {mpicc}",
            f"CCD        = {mpicc}",
            "FCS        = gfortran",
            f"CFLAGS        = {_BASE_CFLAGS}",
            "CLIBFLAGS    = -shared -fPIC",
            "LDFLAGS        = -lz -lm -lrt -pthread -Xlinker --no-as-needed",
            "CP        = cp",
            "FLEX        = flex",
            "LN        = ln",
            "MKDIR        = mkdir -p",
            "MV        = mv",
            "RANLIB        = echo",
            "BISON        = bison",
            "",
        ]
    )


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
class Check:
    """One preflight result."""

    def __init__(self, name, ok, detail="", fix=""):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.fix = fix


def _flex_version_ok():
    """(ok, version_str). Scotch needs flex >= 2.6.4; older flex silently
    falls back to a lexer without the _32/_64 rename prefix, producing a
    library with `undefined symbol: _SCOTCHyy_NNlex` at load."""
    exe = shutil.which("flex")
    if not exe:
        return False, None
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return False, None
    import re

    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if not m:
        return False, out.strip()
    ver = tuple(int(x) for x in m.groups())
    return ver >= (2, 6, 4), ".".join(map(str, ver))


def _zlib_headers_ok():
    """Can we compile+link against zlib? (dev headers present)."""
    cc = _find_cc()
    if not cc:
        return False
    src = "#include <zlib.h>\nint main(void){return 0;}\n"
    with tempfile.TemporaryDirectory() as td:
        try:
            p = subprocess.run(
                [cc, "-xc", "-", "-o", os.path.join(td, "a.out"), "-lz"],
                input=src,
                text=True,
                capture_output=True,
                timeout=60,
            )
            return p.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False


def _find_cc():
    return shutil.which("gcc") or shutil.which("cc")


def preflight(parallel: bool):
    """Return a list[Check]. `.ok` False on any entry means do not build."""
    from .doctor import _scotch_install_hint, _mpi_install_hint, _distro_family

    fam = _distro_family()
    checks = []

    cc = _find_cc()
    checks.append(
        Check(
            "C compiler",
            bool(cc),
            cc or "not found",
            {
                "debian": "sudo apt install build-essential",
                "fedora": "sudo dnf install gcc make",
            }.get(fam, "install gcc/clang and make"),
        )
    )
    make = shutil.which("make")
    checks.append(
        Check("make", bool(make), make or "not found", "install make (build-essential / gcc make)")
    )

    flex_ok, flex_ver = _flex_version_ok()
    checks.append(
        Check(
            "flex >= 2.6.4",
            flex_ok,
            flex_ver or "not found",
            {"debian": "sudo apt install flex", "fedora": "sudo dnf install flex"}.get(
                fam, "install flex >= 2.6.4 (older flex breaks the lexer symbols)"
            ),
        )
    )
    bison = shutil.which("bison")
    checks.append(
        Check(
            "bison",
            bool(bison),
            bison or "not found",
            {"debian": "sudo apt install bison", "fedora": "sudo dnf install bison"}.get(
                fam, "install bison"
            ),
        )
    )

    checks.append(
        Check(
            "zlib headers",
            _zlib_headers_ok(),
            "zlib.h compilable" if _zlib_headers_ok() else "zlib.h / -lz missing",
            {"debian": "sudo apt install zlib1g-dev", "fedora": "sudo dnf install zlib-devel"}.get(
                fam, "install the zlib development headers"
            ),
        )
    )

    if parallel:
        mpicc = shutil.which("mpicc")
        checks.append(
            Check("mpicc (for PT-Scotch)", bool(mpicc), mpicc or "not found", _mpi_install_hint())
        )

    return checks


# ---------------------------------------------------------------------------
# Failures with clear messages
# ---------------------------------------------------------------------------
class BuildError(Exception):
    """Raised for any build-scotch failure; message is user-facing."""


def _diagnose_make_output(text: str) -> str:
    """Map known Scotch build failure signatures to an actionable hint.

    Ordered most-specific first; the generic library checks look for real
    error signatures (a missing header / undefined reference), NOT merely the
    presence of `-lz`/`mpicc` in a command line — those appear in every build.
    """
    import re

    if "_SCOTCHyy" in text and "lex" in text:
        return (
            "The lexer symbols are unsuffixed — the classic sign of a flex older "
            "than 2.6.4. Install flex >= 2.6.4 and rebuild."
        )
    m = re.search(r"implicit declaration of function .(SCOTCH_[A-Za-z0-9_]+)", text)
    if m and "did you mean" in text:
        fn = m.group(1)
        return (
            f"This Scotch release's symbol-rename table is missing {fn}: under "
            "-DSCOTCH_RENAME_ALL a Fortran stub calls the unsuffixed name, which "
            "is not declared. Known upstream bug in 7.0.12 (SCOTCH_meshBuildElem). "
            "Build a different version (e.g. 7.0.11), or apply "
            "patches/scotch-7.0.12-rename-all-fix.patch to the source tree."
        )
    if "fatal error: zlib.h" in text or "undefined reference to `gz" in text:
        return "zlib development headers/library missing (install zlib1g-dev / zlib-devel)."
    if "fatal error: mpi.h" in text or "mpicc: command not found" in text:
        return "MPI toolchain problem — check that mpicc works (see the PT-Scotch preflight)."
    if "reallocarray" in text:
        return "A libc/reallocarray mismatch — unusual; please report with the log above."
    return ""


# ---------------------------------------------------------------------------
# Download + extract
# ---------------------------------------------------------------------------
def _resolve_source(version, url, sha256):
    if url is None:
        url = _GITLAB.format(v=version)
    if sha256 is None:
        sha256 = _KNOWN_VERSIONS.get(version)
    return url, sha256


def _download(url, sha256, dest: Path):
    print(f"  Downloading {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 (https URL)
            data = r.read()
    except Exception as e:  # urllib raises many types
        raise BuildError(f"Download failed: {e}")

    digest = hashlib.sha256(data).hexdigest()
    if sha256 is None:
        print(
            f"  ! No pinned checksum for this version; got sha256={digest}\n"
            "    (pass --sha256 to verify, or trust this value on re-runs)"
        )
    elif digest != sha256:
        raise BuildError(
            "Checksum mismatch — refusing to build.\n"
            f"    expected {sha256}\n"
            f"    got      {digest}\n"
            "    If you trust this source (e.g. GitLab regenerated the archive), "
            "re-run with --sha256 <the-got-value>."
        )
    dest.write_bytes(data)
    print(f"  Saved {len(data) // 1024} KiB, sha256 OK")


def _extract(tarball: Path, workdir: Path) -> Path:
    print("  Extracting source")
    try:
        with tarfile.open(tarball) as tf:
            _safe_extract(tf, workdir)
    except (tarfile.TarError, OSError) as e:
        raise BuildError(f"Failed to extract {tarball.name}: {e}")
    roots = [p for p in workdir.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise BuildError(f"Unexpected archive layout: {[p.name for p in roots]}")
    return roots[0]


def _safe_extract(tf: tarfile.TarFile, dest: Path):
    """Extract, refusing members that escape dest (path traversal guard)."""
    dest = dest.resolve()
    for m in tf.getmembers():
        target = (dest / m.name).resolve()
        if not str(target).startswith(str(dest)):
            raise BuildError(f"Unsafe path in archive: {m.name}")
    tf.extractall(dest)


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------
def _run_make(src: Path, target: str, cflags: str, log: list):
    """Run one `make <target>` in src, streaming captured output into `log`.
    Raises BuildError with a diagnosis on failure."""
    cmd = ["make", target, f"CFLAGS={cflags}"]
    print(f"  make {target} ...")
    proc = subprocess.run(cmd, cwd=src, capture_output=True, text=True)
    log.append(f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-25:])
        hint = _diagnose_make_output(proc.stdout + proc.stderr)
        msg = f"`make {target}` failed (exit {proc.returncode}).\n\n--- last output ---\n{tail}"
        if hint:
            msg += f"\n\nLikely cause: {hint}"
        raise BuildError(msg)


def _build_libs(src: Path, bits: int, parallel: bool, cc: str, mpicc: str) -> Path:
    """Compile Scotch in `src`; return the dir holding the built .so files."""
    (src / "src" / "Makefile.inc").write_text(_makefile_inc(cc, mpicc))
    suffix = f"_{bits}"
    cflags = _BASE_CFLAGS + (" -DINTSIZE64" if bits == 64 else "")
    cflags += f" -DSCOTCH_NAME_SUFFIX={suffix} -DSCOTCH_RENAME_ALL"

    srcdir = src / "src"
    log = []
    # realclean is best-effort (fresh tree has nothing to clean)
    subprocess.run(["make", "realclean"], cwd=srcdir, capture_output=True, text=True)
    _run_make(srcdir, "libscotch", cflags, log)
    if parallel:
        _run_make(srcdir, "libptscotch", cflags, log)

    libout = src / "lib"
    if not (libout / "libscotch.so").exists():
        raise BuildError(
            "Build reported success but libscotch.so is missing.\n"
            f"    Looked in {libout}\n--- log tail ---\n" + "\n".join(log)[-1500:]
        )
    return libout


def _compile_compat(dest_lib: Path, cc: str):
    """Compile the FILE*/error-capture shim next to the built libs."""
    src = Path(__file__).parent / "native" / "file_compat.c"
    out = dest_lib / "libpyscotch_compat.so"
    p = subprocess.run(
        [cc, "-shared", "-fPIC", "-O2", "-o", str(out), str(src)],
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise BuildError(f"Failed to compile the compat shim:\n{p.stderr}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build(version, bits, parallel, url=None, sha256=None, force=False):
    """Full build pipeline. Returns the build key on success."""
    if platform.system() != "Linux":
        raise BuildError(
            f"scotch build currently supports Linux only (this is {platform.system()}). "
            "On macOS/Windows use conda-forge scotch/ptscotch, or a system package."
        )

    key = _store.make_key(version, bits, parallel)
    dest = _store.build_dir(key)
    if dest.exists() and not force:
        if _store.has_lib(key, parallel):
            print(f"Build {key} already exists (use --force to rebuild).")
            return key
        shutil.rmtree(dest)  # incomplete leftover

    # 1. Preflight — hard stop before any network/compile.
    print(f"Preflight for {key}:")
    checks = preflight(parallel)
    _print_checks(checks)
    failed = [c for c in checks if not c.ok]
    if failed:
        lines = "\n".join(f"  - {c.name}: {c.fix}" for c in failed)
        raise BuildError("Missing build prerequisites. Install them and retry:\n" + lines)

    cc = _find_cc()
    mpicc = shutil.which("mpicc") or "mpicc"
    url, sha256 = _resolve_source(version, url, sha256)

    _store.cache_dir().mkdir(parents=True, exist_ok=True)
    tarball = _store.cache_dir() / f"scotch-v{version}.tar.gz"

    with tempfile.TemporaryDirectory(prefix="pyscotch-build-") as td:
        work = Path(td)
        _download(url, sha256, tarball)
        srcroot = _extract(tarball, work)
        print(f"Building Scotch {version} ({bits}-bit, {'parallel' if parallel else 'sequential'})")
        libout = _build_libs(srcroot, bits, parallel, cc, mpicc)

        # 4. Stage into the store.
        libdir = _store.build_lib_dir(key)
        if libdir.exists():
            shutil.rmtree(libdir)
        libdir.mkdir(parents=True)
        for so in libout.glob("lib*scotch*.so"):
            shutil.copy2(so, libdir / so.name)
        _compile_compat(libdir, cc)

    print(f"\n✓ Built {key}  ->  {libdir}")
    return key


# ---------------------------------------------------------------------------
# CLI handlers
# ---------------------------------------------------------------------------
def _print_checks(checks):
    for c in checks:
        mark = "✓" if c.ok else "✗"
        print(f"  {mark} {c.name:<22} {c.detail}")


def cmd_build(args):
    parallel = _resolve_parallel(args)
    try:
        key = build(
            args.version,
            bits=int(args.int_size),
            parallel=parallel,
            url=args.url,
            sha256=args.sha256,
            force=args.force,
        )
    except BuildError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    if args.use:
        _store.set_default_key(key)
        print(f"Set {key} as the default (PyScotch will now load it).")
    else:
        print(f"Run `pyscotch scotch use {key}` to make it the default.")
    return 0


def _resolve_parallel(args):
    """--parallel / --sequential explicit; otherwise ask (no surprise)."""
    if args.parallel:
        return True
    if args.sequential:
        return False
    # Interactive prompt; default sequential if not a TTY.
    if not sys.stdin.isatty():
        print("No --parallel/--sequential given and not a TTY; defaulting to sequential.")
        return False
    ans = input("Build parallel PT-Scotch too (needs MPI)? [y/N] ").strip().lower()
    return ans in ("y", "yes")


def cmd_list(args):
    keys = _store.list_keys()
    default = _store.get_default_key()
    if not keys:
        print("No locally built Scotch. Build one with `pyscotch scotch build`.")
        return 0
    print("Locally built Scotch libraries:")
    for k in keys:
        info = _store.parse_key(k)
        mark = "*" if k == default else " "
        variant = "parallel" if info["parallel"] else "sequential"
        print(f" {mark} {k:<20} {info['bits']}-bit {variant:<10} {_store.build_lib_dir(k)}")
    if default:
        print(f"\n* = default (loaded when its width/variant matches the run).")
    else:
        print("\nNo default set. `pyscotch scotch use <key>` to pick one.")
    return 0


def cmd_use(args):
    if _store.parse_key(args.key) is None or not _store.build_dir(args.key).is_dir():
        print(f"Error: no such build '{args.key}'. See `pyscotch scotch list`.", file=sys.stderr)
        return 1
    _store.set_default_key(args.key)
    print(f"Default set to {args.key}.")
    return 0


def cmd_rm(args):
    d = _store.build_dir(args.key)
    if not d.is_dir():
        print(f"Error: no such build '{args.key}'.", file=sys.stderr)
        return 1
    if _store.get_default_key() == args.key:
        _store.clear_default()
        print(f"(was the default; default cleared)")
    shutil.rmtree(d)
    print(f"Removed {args.key}.")
    return 0
