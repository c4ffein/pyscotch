#!/usr/bin/env bash
# Build the sequential-only Scotch libraries (32- and 64-bit int variants, with
# _32/_64 symbol suffixes) plus the PyScotch compat layer, and stage exactly the
# files needed at runtime into pyscotch/_libs/lib{32,64}/ so they are picked up
# as package data by wheel builds.
#
# Designed to run both:
#   - on a dev machine (deps assumed present, or installable via apt),
#   - inside a manylinux container as cibuildwheel's CIBW_BEFORE_ALL
#     (installs zlib-devel/flex/bison via dnf or yum when missing).
#
# MPI/PT-Scotch is intentionally out of scope: wheels ship the sequential
# variant only.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# 1. Ensure build dependencies (needed in bare manylinux containers)
# ---------------------------------------------------------------------------
missing=()
command -v flex >/dev/null 2>&1 || missing+=(flex)
command -v bison >/dev/null 2>&1 || missing+=(bison)
command -v make >/dev/null 2>&1 || missing+=(make)
command -v gcc >/dev/null 2>&1 || missing+=(gcc)
command -v m4 >/dev/null 2>&1 || missing+=(m4)  # needed to build flex from source (below)
# patchelf: Scotch builds libscotch.so via `gcc -shared -o` WITHOUT its
# LDFLAGS, so the .so calls libz/libm/libpthread but records no DT_NEEDED for
# them (see step 3b). We patch the NEEDED list back in; auditwheel then vendors
# libz. The package is named `patchelf` on dnf/yum and apt alike.
command -v patchelf >/dev/null 2>&1 || missing+=(patchelf)
if ! printf '#include <zlib.h>\nint main(void){return 0;}\n' \
        | gcc -xc - -o /dev/null -lz 2>/dev/null; then
    missing+=(zlib-devel)
fi

if [ "${#missing[@]}" -gt 0 ]; then
    echo "Installing missing build dependencies: ${missing[*]}"
    if command -v dnf >/dev/null 2>&1; then
        dnf install -y "${missing[@]}"
    elif command -v yum >/dev/null 2>&1; then
        yum install -y "${missing[@]}"
    elif command -v apt-get >/dev/null 2>&1; then
        # Debian/Ubuntu naming differs for zlib
        deps=()
        for p in "${missing[@]}"; do
            if [ "$p" = "zlib-devel" ]; then deps+=(zlib1g-dev); else deps+=("$p"); fi
        done
        ${SUDO:-} apt-get update && ${SUDO:-} apt-get install -y "${deps[@]}"
    else
        echo "ERROR: missing build dependencies (${missing[*]}) and no supported" >&2
        echo "package manager (dnf/yum/apt-get) found. Install them manually." >&2
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# 1b. Ensure flex >= 2.6.4
# ---------------------------------------------------------------------------
# Scotch's Makefile rejects older flex (e.g. the 2.6.1 that AlmaLinux 8 /
# manylinux_2_28 ships) as "bogus" and SILENTLY falls back to a pre-generated
# last_resort lexer that does NOT carry the _32/_64 rename prefix. Bison still
# emits a parser calling `_SCOTCHyy_32lex`, so the built libscotch.so ends up
# with `undefined symbol: _SCOTCHyy_32lex` at load. The distro packages only
# ship 2.6.1, so when the system flex is too old we build 2.6.4 from source.
flex_ok=0
if command -v flex >/dev/null 2>&1; then
    fv="$(flex --version 2>/dev/null | grep -oE '[0-9]+(\.[0-9]+)+' | head -1)"
    if [ -n "$fv" ] && [ "$(printf '2.6.4\n%s\n' "$fv" | sort -V | head -1)" = "2.6.4" ]; then
        flex_ok=1
    fi
fi
if [ "$flex_ok" -ne 1 ]; then
    echo "System flex is missing or < 2.6.4 ($(flex --version 2>/dev/null || echo none)); building flex 2.6.4 from source"
    ftmp="$(mktemp -d)"
    (
        cd "$ftmp"
        curl -LsSf https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz -o flex.tar.gz
        tar xzf flex.tar.gz
        cd flex-2.6.4
        ./configure --prefix=/usr/local >/dev/null
        make -j"$(nproc)" >/dev/null
        ${SUDO:-} make install >/dev/null
    )
    rm -rf "$ftmp"
    export PATH="/usr/local/bin:$PATH"
    hash -r
    echo "flex is now: $(flex --version)"
fi

# ---------------------------------------------------------------------------
# 2. Build sequential-only Scotch (both int sizes) + compat layer
# ---------------------------------------------------------------------------
make build-seq-only

# ---------------------------------------------------------------------------
# 3. Stage exactly the runtime .so files into the wheel package-data location
# ---------------------------------------------------------------------------
DEST="$REPO_ROOT/pyscotch/_libs"
rm -rf "$DEST"
for size in 32 64; do
    mkdir -p "$DEST/lib$size"
    for f in libscotch.so libscotcherr.so libpyscotch_compat.so; do
        src="$REPO_ROOT/scotch-builds/lib$size/$f"
        if [ ! -f "$src" ]; then
            echo "ERROR: expected library not found: $src" >&2
            exit 1
        fi
        cp -f "$src" "$DEST/lib$size/$f"
    done
done

# ---------------------------------------------------------------------------
# 3b. Record the DT_NEEDED entries Scotch's build omits
# ---------------------------------------------------------------------------
# Root cause (upstream): Scotch builds the shared object with
# `gcc -shared -o libscotch.so *.o` (Makefile.inc AR/ARFLAGS) and applies its
# `-lz -lm -pthread` LDFLAGS only when linking the command-line *executables*.
# So libscotch.so calls gz*/pthread_*/sqrt but declares NEEDED = libc.so.6 only.
# This is harmless in Scotch's own world (its executables and most distro
# re-links supply the libraries), but it bites a standalone, dlopen'd,
# self-contained wheel: under lazy binding (typical dev boxes) the import still
# works, yet under the eager binding (-z now / full RELRO) the manylinux
# toolchain uses, dlopen resolves every symbol up front and fails with
# `undefined symbol: gzclose`.
#
# The clean fix belongs upstream: link libscotch.so with its libraries, or build
# it with `-Wl,--no-undefined` so the linker *rejects* an under-declared shared
# object instead of shipping one. Worth raising with the Scotch team — it would
# help every downstream that loads the bare .so, not just us. Until then we
# defend in two independent layers, either of which is sufficient:
#   1. HERE (build time): stamp the honest NEEDED entries onto the bundled .so,
#      so the loader is self-sufficient and the artifact is correctly linked for
#      auditwheel and any non-Python consumer.
#   2. pyscotch/libscotch.py `_preload_dependencies` (runtime): preload libz by
#      soname RTLD_GLOBAL before Scotch loads — this also covers an under-linked
#      *system* Scotch, which this build-time step cannot reach.
# Idempotent.
add_needed() {
    local so="$1" soname
    for soname in libz.so.1 libm.so.6 libpthread.so.0; do
        if ! patchelf --print-needed "$so" | grep -qx "$soname"; then
            patchelf --add-needed "$soname" "$so"
        fi
    done
}
for size in 32 64; do
    add_needed "$DEST/lib$size/libscotch.so"
done

echo ""
echo "Staged wheel libraries in pyscotch/_libs/:"
ls -l "$DEST"/lib32 "$DEST"/lib64
echo ""
echo "NEEDED of libscotch.so (must include libz.so.1):"
patchelf --print-needed "$DEST/lib64/libscotch.so"
