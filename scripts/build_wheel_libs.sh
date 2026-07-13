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

echo ""
echo "Staged wheel libraries in pyscotch/_libs/:"
ls -l "$DEST"/lib32 "$DEST"/lib64
