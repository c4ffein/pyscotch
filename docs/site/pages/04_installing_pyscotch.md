# Tutorial: Installing PyScotch

There are several ways to get PyScotch running, from a one-line install to a
full source build. Pick the one that matches your needs:

| You want | Use |
|----------|-----|
| Graph partitioning, ordering, coloring, meshes | **pip / uv wheels** (easiest) |
| Distributed operations with MPI (PT-Scotch) | **Build from source** |
| Your distro's or conda's Scotch package | **System-installed Scotch** |

## 1. Installing with pip or uv

The normal path. Wheels are published on PyPI:

```bash
pip install pyscotch
# or, with uv:
uv pip install pyscotch
```

The wheels bundle the **sequential** Scotch libraries for **both** integer
widths, so `PYSCOTCH_INT_SIZE=32` and `PYSCOTCH_INT_SIZE=64` (the default)
work out of the box — no compiler, no system packages needed.

If you want the scipy/networkx conversion helpers
(`Graph.from_scipy_sparse()`, `Graph.to_networkx()`, ...), install the
`interop` extra:

```bash
pip install "pyscotch[interop]"
```

**What wheels can't do:** MPI. An MPI implementation cannot be bundled in a
wheel, so PT-Scotch (`PYSCOTCH_PARALLEL=1` and the `Dgraph` class) is not
included. For distributed operations, build from source.

## 2. Building from Source

The full experience, including PT-Scotch/MPI. You'll need:

- GCC or Clang, Make
- flex and bison (Scotch's parsers)
- zlib development headers
- An MPI implementation (OpenMPI or MPICH) for the parallel variants

```bash
git clone https://github.com/c4ffein/pyscotch.git
cd pyscotch
git submodule update --init --recursive
make build-all
uv pip install -e ".[dev]"
make test
```

> The Scotch submodule lives on `gitlab.inria.fr`. If the submodule step
> fails, check that your environment can reach that host.

`make build-all` compiles 4 Scotch variants into `scotch-builds/`:
sequential + parallel libraries, each in 32-bit and 64-bit `SCOTCH_Num`
flavors — plus the small `libpyscotch_compat` shim for FILE\* ABI
compatibility. PyScotch finds this development layout automatically.

## 3. Using a System-Installed Scotch

If PyScotch finds neither bundled wheel libraries nor a `scotch-builds/`
directory, it falls back to the system-installed Scotch:

```bash
apt install libscotch-dev                  # Debian/Ubuntu
pip install pyscotch --no-binary pyscotch  # sdist: no bundled libraries
```

You can also force the system library even when others are available:

```bash
PYSCOTCH_SYSTEM=1 python my_script.py
```

One caveat: system packages ship **unsuffixed** symbols and a **single**
integer width. PyScotch verifies the width at load time via
`SCOTCH_numSizeof()` and refuses to load under a mismatched
`PYSCOTCH_INT_SIZE` — the error message tells you the correct value to set.
conda-forge's `scotch` is 64-bit, matching PyScotch's default, so it works
with no configuration at all; if your distro ships a 32-bit build, set:

```bash
PYSCOTCH_SYSTEM=1 PYSCOTCH_INT_SIZE=32 python my_script.py
```

## 4. conda-forge

A conda recipe exists (`packaging/conda/meta.yaml`) but the package is not
yet published on conda-forge. Coming soon — until then, use pip/uv or a
source build inside your conda environment.

## Configuration

PyScotch selects which Scotch variant to load via environment variables,
read at import time:

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `PYSCOTCH_INT_SIZE` | `32`, `64` | `64` | Size of `SCOTCH_Num` integers |
| `PYSCOTCH_PARALLEL` | `0`, `1` | `0` | Load PT-Scotch (parallel) or Scotch (sequential) |
| `PYSCOTCH_LIB_DIR` | path | unset | Explicit directory containing the Scotch libraries |
| `PYSCOTCH_SYSTEM` | `0`, `1` | `0` | Force the system-installed Scotch |

### Library Discovery Order

When you `import pyscotch`, the libraries are located in this order:

1. `PYSCOTCH_SYSTEM=1` — skip straight to the system-installed Scotch
2. `PYSCOTCH_LIB_DIR` — explicit override
3. Libraries bundled inside the installed wheel (`pyscotch/_libs/`)
4. `scotch-builds/` next to the repo (development layout)
5. Fallback: the system-installed Scotch (dlopen by soname)

## Verify Your Install

```python
import pyscotch

print(pyscotch.scotch_version())  # e.g. (7, 0, 11)
```

If that prints a version tuple, you're set. The next page walks through
actually using PyScotch.
