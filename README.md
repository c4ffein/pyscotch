# PyScotch - Python Wrapper for PT-Scotch

A comprehensive Python wrapper for the PT-Scotch library, providing easy access to graph partitioning, mesh partitioning, and sparse matrix ordering capabilities.

## Features

- Full Python API for PT-Scotch library functions
- Command-line interface for common operations
- Easy build system with Makefile
- Support for both sequential (Scotch) and parallel (PT-Scotch) operations
- Graph partitioning, mesh partitioning, and sparse matrix ordering

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

### Python API

```python
from pyscotch import Graph, Mesh, Strategy

# Create a graph
graph = Graph()
graph.load("graph.grf")

# Partition the graph
strategy = Strategy()
partitions = graph.partition(nparts=4, strategy=strategy)

# Save the result
graph.save_mapping("partition.map")
```

### Command Line Interface

```bash
# Partition a graph
pyscotch graph partition input.grf -n 4 -o output.map

# Order a graph for sparse matrix factorization
pyscotch graph order input.grf -o output.ord

# Mesh partitioning
pyscotch mesh partition input.msh -n 8 -o output.map
```

## Documentation

See the `docs/` directory for detailed documentation and examples.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

The PT-Scotch library itself is distributed under the CeCILL-C license.

## Acknowledgments

This wrapper is built on top of the PT-Scotch library developed by François Pellegrini and the Scotch team at INRIA.
