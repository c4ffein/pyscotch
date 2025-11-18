# PyScotch Examples

This directory contains example code demonstrating how to use PyScotch for various graph and mesh processing tasks.

## Examples Overview

### 1. Simple Graph Partitioning
**File:** `simple_partition.py`

**What it demonstrates:**
- Creating graphs from edge lists
- Graph validation
- Partitioning with different strategies
- Analyzing partition quality

**Usage:**
```bash
python simple_partition.py
```

**Output:**
- Shows partition sizes
- Displays partition balance
- Lists vertices in each partition

---

### 2. Graph Ordering
**File:** `graph_ordering.py`

**What it demonstrates:**
- Creating structured graphs (grid)
- Computing vertex orderings
- Applying orderings to arrays
- Using different ordering strategies (nested dissection)

**Usage:**
```bash
python graph_ordering.py
```

**Use case:** Sparse matrix factorization, reducing fill-in

---

### 3. Distributed Graph Coarsening
**File:** `distributed_coarsening.py`

**What it demonstrates:**
- Loading distributed graphs with MPI
- Multi-level graph coarsening
- Cross-process synchronization
- Distributed graph validation

**Usage:**
```bash
mpirun -np 3 python distributed_coarsening.py ../external/scotch/src/check/data/bump.grf
```

**Requirements:** MPI installed (OpenMPI or MPICH)

**Output:**
- Original graph statistics (global and per-rank)
- Coarse graph statistics
- Coarsening ratio
- Multi-level coarsening results

---

### 4. Mesh Partitioning
**File:** `mesh_partitioning.py`

**What it demonstrates:**
- Loading meshes from files
- Mesh partitioning
- Converting mesh to graph
- Partition analysis

**Usage:**
```bash
python mesh_partitioning.py ../external/scotch/src/check/data/m4x4.msh 4
```

**Use case:** Finite element analysis, domain decomposition

---

## Running the Examples

### Prerequisites

1. **Build PyScotch:**
   ```bash
   make build-all
   pip install -e .
   ```

2. **For MPI examples:**
   - Install MPI: `sudo apt-get install openmpi-bin libopenmpi-dev` (Ubuntu/Debian)
   - Or: `brew install open-mpi` (macOS)

### Sequential Examples

Run directly with Python:
```bash
python simple_partition.py
python graph_ordering.py
python mesh_partitioning.py <mesh_file> <num_parts>
```

### Distributed Examples

Run with MPI:
```bash
mpirun -np <num_processes> python distributed_coarsening.py <graph_file>
```

**Example:**
```bash
mpirun -np 3 python distributed_coarsening.py ../external/scotch/src/check/data/bump.grf
```

---

## Test Data

PyScotch includes Scotch test data in `external/scotch/src/check/data/`:

**Graphs:**
- `bump.grf` - Small test graph
- `bump_b100000.grf` - Larger test graph
- `m4x4_b1.grf` - 4x4 mesh graph

**Meshes:**
- `m4x4.msh` - 4x4 mesh
- `m8x8.msh` - 8x8 mesh

---

## Common Operations

### Creating a Graph from Edges
```python
from pyscotch import Graph

edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
graph = Graph.from_edges(edges, num_vertices=4)
```

### Partitioning a Graph
```python
from pyscotch import Graph, Strategies

graph = Graph()
graph.load("my_graph.grf")

# Partition into 4 parts
strategy = Strategies.partition_quality()
mapping = graph.partition(4, strategy)

# Get partition array
partitions = mapping.get_partition_array()
```

### Distributed Graph Operations
```python
from pyscotch import Dgraph
from pyscotch.mpi import mpi
from pyscotch import libscotch as lib

mpi.init()
lib.set_active_variant(64, parallel=True)

# Load distributed graph
dgraph = Dgraph()
dgraph.load("my_graph.grf")

# Coarsen
coarse, mult = dgraph.coarsen(coarrat=0.8)

# Validate
if coarse.check():
    print("Coarse graph validated!")

dgraph.exit()
coarse.exit()
mpi.finalize()
```

---

## Next Steps

After trying these examples, check out:

1. **Tests:** `tests/` directory for more usage patterns
2. **Documentation:** `docs/API.md` for full API reference
3. **MPI Tests:** `tests/scotch_ports_mpi/` for advanced distributed examples

---

## Troubleshooting

### "Cannot find graph file"
Make sure you're in the `examples/` directory or provide the full path to the graph file.

### MPI examples fail
- Check MPI is installed: `mpirun --version`
- Try different number of processes
- Check file paths are accessible from all processes

### Import errors
- Make sure PyScotch is installed: `pip install -e .`
- Check Scotch libraries are built: `ls ../scotch-builds/lib64/`

---

## Contributing

Have a cool example? Submit a PR!

Examples should:
- Be well-commented
- Include usage instructions
- Demonstrate a specific feature
- Be runnable out-of-the-box (with documented test data)

---

**Questions?** Open an issue on GitHub!
