# PyScotch

---
**WARNING: this is a vibe-engineering experiment - you probably shouldn't use this!**
---

Python ctypes wrapper for the [PT-Scotch](https://www.labri.fr/perso/pelegrin/scotch/) graph partitioning library: graph/mesh partitioning, sparse matrix ordering, coloring, and distributed (MPI) graph operations.

> **📖 If you want to *use* PyScotch, start at the documentation site:
> [c4ffein.github.io/pyscotch](https://c4ffein.github.io/pyscotch)** — tutorials
> covering installation, every workflow, parallel/MPI usage, and
> reproducibility, with runnable (CI-tested) examples.
> This README is the developer-facing map of the repository.

## Installation (short version)

```bash
pip install pyscotch          # wheels bundle sequential Scotch, 32- and 64-bit ints
pip install "pyscotch[interop]"   # + scipy/networkx conversion helpers
```

Wheels can't ship MPI. For PT-Scotch (`Dgraph`), compile a parallel Scotch
through the CLI — no root, checksum-pinned source from upstream, with any
needed build quickfixes applied automatically:

```bash
pip install "pyscotch[parallel]"              # + mpi4py
pyscotch scotch build --parallel --use
PYSCOTCH_PARALLEL=1 pyscotch doctor           # verify the full parallel stack
```

When anything misbehaves, `pyscotch doctor` reports which Scotch loaded (and
from where), its capabilities, and the exact command that fixes what's
missing. Details, system/conda Scotch, and troubleshooting: see
[Installing PyScotch](https://c4ffein.github.io/pyscotch).

## Quick Taste

```python
from pyscotch import Graph

graph = Graph.from_edges([(0, 1), (1, 2), (2, 3), (3, 0)])
parts = graph.partition(2)          # numpy array of part indices
permtab, peritab = graph.order()    # nested-dissection ordering
```

There's also a CLI: `pyscotch partition/order/check/info`, `pyscotch doctor`,
and `pyscotch scotch build/list/use/rm/patches` for managing local Scotch
builds.

## Features

- **Graph partitioning** — sequential and distributed (MPI)
- **Mesh partitioning** — with mesh-to-graph conversion
- **Sparse matrix ordering** — nested dissection for reduced fill-in
- **Graph coloring** — greedy heuristic coloring
- **Distributed graph operations** — coarsening, growing, band extraction, redistribution, induced subgraphs
- **Safe strategy strings** — `Strategy(string)` is validated against the live library's own parsers at construction (Scotch's grammar accepts silently-do-nothing strings; PyScotch refuses them), plus a typed builder (`pyscotch.strategy_grammar`) that makes the degenerate forms unrepresentable
- **Reproducibility, Scotch's way** — explicit `random_reset()`/`random_seed()` mirroring the C API, no implicit PRNG resets; under deterministic settings PyScotch's partitions are byte-identical to Scotch's own `gpart`
- **Managed Scotch builds** — `pyscotch scotch build` downloads, patches (when upstream needs it), compiles, and selects local libraries; wheels, system, conda, and dev builds coexist
- **Multi-variant loading** — 32/64-bit integer builds with `_32`/`_64` symbol suffixes, sequential and parallel
- **No hard mpi4py dependency** — bundled lightweight MPI ctypes wrapper (mpi4py supported and recommended for real MPI apps)

## Configuration

Environment variables, read at import time:

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `PYSCOTCH_INT_SIZE` | `32`, `64` | `64` | Size of `SCOTCH_Num` integers |
| `PYSCOTCH_PARALLEL` | `0`, `1` | `0` | Load PT-Scotch (parallel) or Scotch (sequential) |
| `PYSCOTCH_LIB_DIR` | path | unset | Explicit directory containing the Scotch libraries |
| `PYSCOTCH_SYSTEM` | `0`, `1` | `0` | Force the system-installed Scotch (distro/conda packages) |

Library discovery order on `import pyscotch`:

1. `PYSCOTCH_SYSTEM=1` — skip straight to the system Scotch
2. `PYSCOTCH_LIB_DIR` — explicit override
3. The managed build selected with `pyscotch scotch use` (under `~/.local/share/pyscotch`, override with `PYSCOTCH_HOME`)
4. Libraries bundled inside the installed wheel (`pyscotch/_libs/`)
5. `scotch-builds/` next to the repo (development layout)
6. Fallback: system-installed Scotch (dlopen by soname; unsuffixed symbols, single width — verified via `SCOTCH_numSizeof()`, with a mismatch refused at load)

## Development Setup

```bash
git clone https://github.com/c4ffein/pyscotch.git
cd pyscotch
git submodule update --init --recursive
make build-all
uv pip install -e ".[dev]"
```

Prerequisites: GCC or Clang, Make, flex ≥ 2.6.4, bison, zlib headers, and an
MPI implementation (OpenMPI or MPICH) for the parallel variants.

> The Scotch submodule lives on `gitlab.inria.fr`; if the submodule step
> fails, check that your environment can reach that host. Builds never
> compile the submodule in place — `make` prepares a disposable, quickfix-
> patched copy under `build/scotch-src/` (via `pyscotch scotch prepare`), so
> the submodule stays pristine.

`make build-all` compiles 4 Scotch variants into `scotch-builds/`:

| Directory | Contents |
|-----------|----------|
| `lib32/`, `lib64/` | Sequential + parallel libraries, 32/64-bit `SCOTCH_Num` |
| `inc32/`, `inc64/` | Matching headers |

plus `libpyscotch_compat`, a small C shim giving Scotch `FILE*`s opened by
the same C runtime it was compiled against.

## Testing

```bash
make test           # default: 64-bit parallel, no hypothesis
make test-full      # full suite including hypothesis
make test-quadrant  # all 4 variants (32/64 × seq/par) with hypothesis
```

| Tier | What it proves |
|------|----------------|
| `tests/scotch_ports/`, `tests/scotch_ports_mpi/` | Direct ports of Scotch's C tests (MPI ones run via mpirun) |
| `tests/pyscotch_base/` | PyScotch-specific: API completeness, int sizes, symbol prefixes, strategy structure |
| `tests/hypothesis/` | Property-based tests — stronger validation than Scotch's own C tests |
| `tests/pyscotch_integration/` | End-to-end orchestrated workflows |
| `tests/golden/` + `scripts/golden_walkthrough.py` | Golden master: the full sdist user journey, byte-for-byte |
| `tests/pyscotch_base/test_differential_gpart.py` | Differential: byte-identity with Scotch's own `gpart` (opt-in via `PYSCOTCH_GPART`) |
| `docs/site/examples/` | Every doc example runs as a test |

CI additionally builds Scotch from the upstream tarball through the CLI
(pre-release, from the repo: `scotch-build.yml`) and re-runs the same journey
against the published package (post-release, from PyPI: `pypi-verify.yml`).

## Project Structure

```
pyscotch/
  __init__.py          # Public API exports
  libscotch.py         # ctypes bindings, library discovery/loading, type definitions
  graph.py             # Sequential graph operations
  dgraph.py            # Distributed graph operations (MPI)
  mesh.py              # Mesh operations
  strategy.py          # Strategy management + construction-time string validation
  strategy_grammar.py  # Typed builder for strategy strings
  arch.py              # Target architecture definitions
  mapping.py           # Mapping result container
  ordering.py          # Ordering result container
  context.py           # SCOTCH_Context (per-context options, private PRNG streams)
  mpi.py               # Minimal MPI wrapper (OpenMPI, MPICH, Intel MPI)
  doctor.py            # `pyscotch doctor` environment diagnostics
  scotch_build.py      # `pyscotch scotch` — download/patch/compile/manage Scotch builds
  _store.py            # Managed-build store (~/.local/share/pyscotch)
  _patches/            # Bundled quickfix patches for upstream releases
  api_decorators.py    # @scotch_binding / @highlevel_api tracking
  cli.py               # Command-line interface
  native/
    file_compat.c      # FILE* ABI compatibility layer
docs/site/             # Homegrown docs generator → c4ffein.github.io/pyscotch
external/
  scotch/              # Scotch submodule (gitlab.inria.fr) — pristine, never built in place
```

## How It Works

PyScotch uses ctypes to call Scotch's C functions directly. Key design decisions:

- **Dynamic struct sizing** via `SCOTCH_*Sizeof()` — never hardcodes structure sizes
- **Symbol suffixes** (`_32`/`_64`) via `SCOTCH_NAME_SUFFIX` — allows loading multiple variants
- **FILE\* compatibility layer** — a small C shim (`libpyscotch_compat`) that opens files with the same C runtime Scotch was compiled against, avoiding ABI mismatches
- **Scotch stays the semantic authority** — strategy strings, PRNG behavior, and defaults are Scotch's own; PyScotch validates and surfaces, never reinterprets
- **`@scotch_binding` decorators** — track which C functions each Python method wraps, enabling automated API completeness checks

## Versioning

PyScotch versions are `X.Y.z`, where **`X.Y` mirrors the Scotch series it is
built and tested against** (e.g. PyScotch `7.0.*` supports Scotch 7.0.x) and
**`z` counts PyScotch's own releases** within that series. Pin accordingly,
e.g. `pyscotch~=7.0.2`. Use `pyscotch.scotch_version()` to check the Scotch
actually loaded at runtime.

## License

MIT License. See [LICENSE](LICENSE).

PT-Scotch itself is distributed under the [CeCILL-C](https://cecill.info/licences/Licence_CeCILL-C_V1-en.html) license.

## Acknowledgments

Built on [PT-Scotch](https://www.labri.fr/perso/pelegrin/scotch/) by Francois Pellegrini and the Scotch team at INRIA Bordeaux.
