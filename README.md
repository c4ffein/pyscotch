# PyScotch - Python Wrapper for PT-Scotch

A comprehensive Python wrapper for the PT-Scotch library, providing easy access to graph partitioning, mesh partitioning, and sparse matrix ordering capabilities with **100% distributed graph operation coverage**! 🎯

## ✨ What's New in v0.2.0

🎉 **Phase 1 Complete!** All Scotch distributed graph operations now implemented:
- ✅ **`Dgraph.ghst()`** - Ghost edge computation
- ✅ **`Dgraph.grow()`** - Region growing (adaptive mesh refinement)
- ✅ **`Dgraph.band()`** - Band graph extraction (sparse matrix reordering)
- ✅ **`Dgraph.redist()`** - Graph redistribution (dynamic load balancing)
- ✅ **`Dgraph.induce_part()`** - Induced subgraph extraction

**Coverage:** 6/6 Scotch operations = 100%! | **Tests:** 192 passing | **Completion:** 80%

## Features

### Core Capabilities
- ✅ **Full Python API** for PT-Scotch library functions
- ✅ **Multi-variant architecture** - Load 4 Scotch variants simultaneously (32/64-bit × seq/parallel)
- ✅ **Complete distributed operations** - All 6 Scotch dgraph operations implemented
- ✅ **Type hints** - Full typing support for better IDE experience
- ✅ **RAII resource management** - Automatic cleanup with context managers

### Operations
- ✅ **Graph partitioning** - Sequential and distributed
- ✅ **Mesh partitioning** - With graph conversion
- ✅ **Sparse matrix ordering** - For reduced fill-in
- ✅ **Graph coarsening** - Multi-level with folding support
- ✅ **Region growing** - From seed vertices
- ✅ **Graph redistribution** - Dynamic load balancing
- ✅ **Band extraction** - For sparse matrices
- ✅ **Induced subgraphs** - Hierarchical partitioning

### Quality Assurance
- ✅ **192 passing tests** - Including 11 MPI tests
- ✅ **Integration tests** - End-to-end workflows
- ✅ **Benchmarks** - Performance validation
- ✅ **Examples** - Ready-to-run code

## Installation

### Prerequisites

- Python 3.7+
- GCC/Clang compiler
- MPI implementation (OpenMPI or MPICH) for PT-Scotch
- Make
- Git

### Setup

1. Clone this repository:
```bash
git clone <your-repo-url>
cd pyscotch
```

2. Add the Scotch submodule (requires access to GitLab):
```bash
git submodule add https://gitlab.inria.fr/scotch/scotch.git external/scotch
git submodule update --init --recursive
```

Note: If you encounter access issues with the GitLab repository, you may need to configure authentication or use an SSH key.

3. Build the Scotch library:
```bash
make build-scotch
```

4. Install the Python package:
```bash
pip install -e .
```

## Quick Start

### Sequential Graph Partitioning

```python
from pyscotch import Graph, Strategies

# Create and load graph
graph = Graph.from_edges([(0,1), (1,2), (2,3), (3,0)], num_vertices=4)

# Partition with quality strategy
strategy = Strategies.partition_quality()
mapping = graph.partition(4, strategy)

# Analyze results
parttab = mapping.get_partition_array()
print(f"Partition sizes: {mapping.get_partition_sizes()}")
```

### Distributed Graph Operations (MPI)

```python
from pyscotch import Dgraph, libscotch as lib
from pyscotch.mpi import mpi

# Initialize MPI
mpi.init()
lib.set_active_variant(64, parallel=True)

# Load distributed graph
dgraph = Dgraph()
dgraph.load("graph.grf")

# Coarsen (multi-level)
coarse, mult = dgraph.coarsen(coarrat=0.8)
if mult is not None:
    print(f"Coarsened successfully!")
    coarse.exit()

dgraph.exit()
mpi.finalize()
```

### Region Growing (NEW!)

```python
from pyscotch import Dgraph
from pyscotch.mpi import mpi
import numpy as np

mpi.init()
dgraph = Dgraph()
dgraph.load("graph.grf")

# Compute ghost edges
dgraph.ghst()

# Grow from seeds
seedloctab = np.array([0, 10, 20], dtype=np.int64)
partgsttab = np.full(vertgstnbr, -1, dtype=np.int64)
dgraph.grow(3, seedloctab, 4, partgsttab)

dgraph.exit()
mpi.finalize()
```

## Examples

See `examples/` directory for complete working examples:
- **`simple_partition.py`** - Basic graph partitioning
- **`graph_ordering.py`** - Sparse matrix ordering
- **`distributed_coarsening.py`** - MPI coarsening workflow
- **`mesh_partitioning.py`** - Mesh partitioning and conversion

Run examples:
```bash
# Sequential
python examples/simple_partition.py

# MPI
mpirun -np 4 python examples/distributed_coarsening.py external/scotch/src/check/data/bump.grf
```

## Benchmarks

Performance benchmarks available in `benchmarks/`:

```bash
# Sequential partitioning
python benchmarks/benchmark_sequential_partitioning.py graph.grf 4

# Distributed operations
mpirun -np 4 python benchmarks/benchmark_distributed_operations.py graph.grf
```

See `benchmarks/README.md` for details.

## Testing

Run the full test suite:
```bash
make test  # Runs pytest -vvvv
```

Or run specific tests:
```bash
# Sequential tests
pytest tests/pyscotch_base/ -v

# Integration tests
pytest tests/integration/ -v

# MPI tests
mpirun -np 3 pytest tests/scotch_ports_mpi/ -v
```

### Pipeline Limitations

CI runners use `PYSCOTCH_MPI_OVERSUBSCRIBE=1` to allow MPI tests with more processes than available CPU slots. This uses `mpirun --oversubscribe` which doesn't reflect true multi-node behavior - all processes share memory and CPU time on a single machine.

## Documentation

Comprehensive documentation available:
- **`docs/API.md`** - Full API reference
- **`ROADMAP.md`** - Project status and plans
- **`MPI_TEST_COVERAGE.md`** - Distributed operation coverage
- **`examples/README.md`** - Example documentation
- **`benchmarks/README.md`** - Benchmark documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

The PT-Scotch library itself is distributed under the CeCILL-C license.

## Acknowledgments

This wrapper is built on top of the PT-Scotch library developed by François Pellegrini and the Scotch team at INRIA.
