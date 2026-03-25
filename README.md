# PyScotch

---
**WARNING: this is a vibe-engineering experiment - you probably shouldn't use this!**
---

Python ctypes wrapper for the [PT-Scotch](https://www.labri.fr/perso/pelegrin/scotch/) graph partitioning library.

PyScotch provides a Pythonic interface to Scotch's graph/mesh partitioning, sparse matrix ordering, and distributed graph operations — without requiring mpi4py or Cython.

## Features

- **Graph partitioning** — sequential and distributed (MPI)
- **Mesh partitioning** — with mesh-to-graph conversion
- **Sparse matrix ordering** — nested dissection for reduced fill-in
- **Graph coloring** — greedy heuristic coloring
- **Distributed graph operations** — coarsening, growing, band extraction, redistribution, induced subgraphs
- **Multi-variant builds** — 32/64-bit integer support with `_32`/`_64` symbol suffixes
- **No mpi4py dependency** — custom lightweight MPI ctypes wrapper
- **Property-based testing** — Hypothesis tests for stronger validation than Scotch's own C tests

## Installation

### Prerequisites

- Python 3.7+
- GCC or Clang
- An MPI implementation (OpenMPI or MPICH) for distributed operations
- Make, CMake, Git

### Setup

```bash
git clone https://github.com/c4ffein/pyscotch.git
cd pyscotch
git submodule update --init --recursive
make build-all
uv pip install -e ".[dev]"
```

> The submodule requires access to `gitlab.inria.fr`. If it fails, check your authentication.

### What `build-all` does

Builds 4 Scotch library variants into `scotch-builds/`:

| Directory | Contents |
|-----------|----------|
| `lib32/` | Sequential + parallel libraries, 32-bit `SCOTCH_Num` |
| `lib64/` | Sequential + parallel libraries, 64-bit `SCOTCH_Num` |
| `inc32/` | Headers for 32-bit variant |
| `inc64/` | Headers for 64-bit variant |

Plus a `libpyscotch_compat` shared library that handles FILE\* ABI compatibility between Python's C runtime and Scotch's.

## Quick Start

### Graph Partitioning

```python
from pyscotch import Graph, Strategies

graph = Graph.from_edges([(0,1), (1,2), (2,3), (3,0)], num_vertices=4)
strategy = Strategies.partition_quality()
mapping = graph.partition(4, strategy)
print(mapping.get_partition_array())  # e.g. [0, 1, 2, 3]
```

### Graph Coloring

```python
from pyscotch import Graph

graph = Graph.from_edges([(0,1), (1,2), (2,0)], num_vertices=3)
colors, num_colors = graph.color()
print(f"{num_colors} colors: {colors}")  # 3 colors: [0, 1, 2]
```

### Sparse Matrix Ordering

```python
from pyscotch import Graph, Strategies

graph = Graph()
graph.load("matrix.grf")
strategy = Strategies.ordering_quality()
ordering = graph.order(strategy)
print(ordering.get_permutation())
```

### Distributed Graph (MPI)

```python
from pyscotch import Dgraph
from pyscotch.mpi import mpi

mpi.init()

dgraph = Dgraph()
dgraph.load("graph.grf")

coarse, mult = dgraph.coarsen(coarrat=0.8)
if mult is not None:
    print("Coarsened successfully")
    coarse.exit()

dgraph.exit()
mpi.finalize()
```

## Configuration

PyScotch selects which Scotch variant to load via environment variables:

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `PYSCOTCH_INT_SIZE` | `32`, `64` | `64` | Size of `SCOTCH_Num` integers |
| `PYSCOTCH_PARALLEL` | `0`, `1` | `1` | Load PT-Scotch (parallel) or Scotch (sequential) |

```bash
# Run with 32-bit sequential Scotch
PYSCOTCH_INT_SIZE=32 PYSCOTCH_PARALLEL=0 python my_script.py
```

## Testing

```bash
# Default: 64-bit parallel, no hypothesis
make test

# Full suite including hypothesis
make test-full

# All 4 variants with hypothesis (32/64 x seq/parallel)
make test-quadrant
```

Test categories:

| Directory | What |
|-----------|------|
| `tests/scotch_ports/` | Direct ports of Scotch's C tests |
| `tests/scotch_ports_mpi/` | MPI test ports (run via mpirun) |
| `tests/pyscotch_base/` | PyScotch-specific tests (API completeness, int sizes, symbol prefixes) |
| `tests/hypothesis/` | Property-based tests — stronger than Scotch's own C tests |
| `tests/pyscotch_integration/` | End-to-end orchestrated workflows |

## API Overview

### Sequential

| Class | Key Methods |
|-------|-------------|
| `Graph` | `build()`, `load()`, `save()`, `partition()`, `order()`, `color()`, `induce_list()`, `induce_part()`, `stat()`, `base()`, `from_edges()` |
| `Mesh` | `build()`, `load()`, `save()`, `check()`, `to_graph()`, `partition()` |
| `Architecture` | `complete()`, `complete_weighted()`, `complete_graph()`, `name()`, `size()` |
| `Strategy` | `set()`, `set_default()`, `set_nested_dissection()` |
| `Strategies` | `partition_quality()`, `partition_speed()`, `ordering_quality()`, `ordering_speed()` |
| `scotch_version()` | Returns `(major, minor, patch)` |

### Distributed (MPI)

| Class | Key Methods |
|-------|-------------|
| `Dgraph` | `build()`, `load()`, `save()`, `check()`, `coarsen()`, `ghst()`, `grow()`, `band()`, `redist()`, `induce_part()` |

## Project Structure

```
pyscotch/
  __init__.py          # Public API exports
  libscotch.py         # ctypes bindings, library loading, type definitions
  graph.py             # Sequential graph operations
  dgraph.py            # Distributed graph operations (MPI)
  mesh.py              # Mesh operations
  strategy.py          # Strategy/preset management
  arch.py              # Target architecture definitions
  mapping.py           # Mapping result container
  ordering.py          # Ordering result container
  mpi.py               # Minimal MPI wrapper (OpenMPI, MPICH, Intel MPI)
  api_decorators.py    # @scotch_binding / @highlevel_api tracking
  cli.py               # Command-line interface
  native/
    file_compat.c      # FILE* ABI compatibility layer
external/
  scotch/              # Scotch submodule (gitlab.inria.fr)
scotchpy/              # Official Scotch Python bindings (reference only, not a dependency)
```

## How It Works

PyScotch uses ctypes to call Scotch's C functions directly. Key design decisions:

- **Dynamic struct sizing** via `SCOTCH_*Sizeof()` — never hardcodes structure sizes
- **Symbol suffixes** (`_32`/`_64`) via `SCOTCH_NAME_SUFFIX` — allows loading multiple variants
- **FILE\* compatibility layer** — a small C shim (`libpyscotch_compat`) that opens files with the same C runtime Scotch was compiled against, avoiding ABI mismatches
- **`@scotch_binding` decorators** — track which C functions each Python method wraps, enabling automated API completeness checks

## License

MIT License. See [LICENSE](LICENSE).

PT-Scotch itself is distributed under the [CeCILL-C](https://cecill.info/licences/Licence_CeCILL-C_V1-en.html) license.

## Acknowledgments

Built on [PT-Scotch](https://www.labri.fr/perso/pelegrin/scotch/) by Francois Pellegrini and the Scotch team at INRIA Bordeaux.
