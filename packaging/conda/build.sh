#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Optional FILE* ABI-compat shim
# ---------------------------------------------------------------------------
# pyscotch is a pure-ctypes wrapper: it does NOT link Scotch at build time, it
# dlopen's the conda `scotch`/`ptscotch` libraries at runtime. The one native
# piece is libpyscotch_compat.so — a tiny libc-only shim (pyscotch/native/
# file_compat.c, no Scotch or MPI dependency) that provides FILE* helpers and
# Scotch error-message capture. It is entirely optional: pyscotch's runtime
# loader (pyscotch/libscotch.py `_load_error_capture`) looks for it next to the
# discovered Scotch library and silently skips it when absent.
#
# We compile it with the SAME toolchain as the conda Scotch and drop it in
# $PREFIX/lib so discovery finds it. The runtime loader hard-codes the ".so"
# name, so we name it ".so" on every platform (ctypes.CDLL loads a .so on macOS
# too), rather than following SHLIB_EXT.
"${CC:-cc}" -shared -fPIC -O2 \
    -o "${PREFIX}/lib/libpyscotch_compat.so" \
    pyscotch/native/file_compat.c

# ---------------------------------------------------------------------------
# Install the Python package
# ---------------------------------------------------------------------------
# HAS_BUNDLED_LIBS is false here (no pyscotch/_libs staged), so setup.py builds
# a pure wheel; the conda Scotch is found at runtime via the env's RPATH.
"${PYTHON}" -m pip install . -vv --no-deps --no-build-isolation
