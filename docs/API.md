# PyScotch API Documentation

## Overview

PyScotch provides a Python interface to the PT-Scotch library for graph partitioning, mesh partitioning, and sparse matrix ordering.

## Core Classes

### Graph

The `Graph` class represents a graph structure for partitioning and ordering operations.

#### Creating a Graph

```python
from pyscotch import Graph

# Create an empty graph
graph = Graph()

# Load from file
graph.load("graph.grf")

# Create from edge list
edges = [(0, 1), (1, 2), (2, 0)]
graph = Graph.from_edges(edges, num_vertices=3)

# Build from arrays
import numpy as np
verttab = np.array([0, 2, 4, 6])  # Vertex starts
edgetab = np.array([1, 2, 0, 2, 0, 1])  # Edge targets
graph = Graph()
graph.build(verttab, edgetab)

# From a scipy sparse adjacency matrix (requires scipy; must be square,
# symmetric in structure and values, zero diagonal)
graph = Graph.from_scipy_sparse(A)      # values != 1 become edge loads
A = graph.to_scipy_sparse()             # back to CSR (exact round-trip)

# From a networkx undirected simple graph (requires networkx)
graph, nodes = Graph.from_networkx(G)   # nodes[i] = label of Scotch vertex i
parts = graph.partition(4)              # parts[i] is the part of nodes[i]
H = graph.to_networkx(nodes=nodes)      # back to nx.Graph with original labels
```

#### Graph Operations

```python
# Check validity
is_valid = graph.check()

# Get size
vertnbr, edgenbr = graph.size()

# Partition
partitions = graph.partition(nparts=4)

# Order for sparse matrix factorization
permutation, inverse = graph.order()

# Save
graph.save("output.grf")
graph.save_mapping("partition.map", partitions)
```

### Strategy

The `Strategy` class controls how operations are performed.

#### Creating Strategies

```python
from pyscotch import Strategy, Strategies

# Default strategy (a fresh Strategy IS Scotch's default;
# reset() returns any configured Strategy to this state)
strategy = Strategy()

# Set mapping strategy
strategy.set_recursive_bisection()
strategy.set_multilevel()

# Set ordering strategy
strategy.reset()
strategy.set_nested_dissection()

# Use pre-defined strategies
strategy = Strategies.partition_quality()
strategy = Strategies.partition_fast()
strategy = Strategies.order_quality()
strategy = Strategies.order_fast()
```

### Architecture

The `Architecture` class defines target architectures for mapping.

```python
from pyscotch import Architecture

# Create complete graph architecture
arch = Architecture()
arch.complete(nparts=4)

# Or use static method
arch = Architecture.complete_graph(4)
```

### Mesh

The `Mesh` class handles mesh structures.

```python
from pyscotch import Mesh

# Create and load mesh
mesh = Mesh()
mesh.load("mesh.msh")

# Partition mesh
partitions = mesh.partition(nparts=8)

# Convert to graph
graph = mesh.to_graph()

# Save
mesh.save("output.msh")
mesh.save_mapping("partition.map", partitions)
```

### Mapping

The `Mapping` class represents partition assignments.

```python
from pyscotch import Mapping

# Create from array
mapping = Mapping(partition_array)

# Analyze
num_parts = mapping.num_partitions()
balance = mapping.balance()
sizes = mapping.get_partition_sizes()
vertices_in_part = mapping.get_partition(0)

# Access
domain = mapping[vertex_idx]

# Save/Load
mapping.save("partition.map")
mapping = Mapping.load("partition.map")
```

### Ordering

The `Ordering` class represents vertex orderings.

```python
from pyscotch import Ordering

# Create from permutation
ordering = Ordering(permutation, inverse_permutation)

# Apply ordering
reordered = ordering.apply(array)
restored = ordering.apply_inverse(reordered)

# Access
new_pos = ordering[old_pos]

# Save/Load
ordering.save("ordering.ord")
ordering = Ordering.load("ordering.ord")
```

### Dgraph (PT-Scotch, MPI)

The `Dgraph` class handles distributed graphs. It requires the parallel
variant (`PYSCOTCH_PARALLEL=1`) and an MPI runtime (scripts launched via
`mpirun`); every operation below is a collective call.

```python
from pyscotch import Dgraph
from pyscotch.mpi import mpi
from pyscotch.graph import Graph
from pyscotch.arch import Architecture

mpi.init()
rank = mpi.comm_rank()

# Create and load a distributed graph (root reads, all ranks participate)
dgraph = Dgraph()
dgraph.load("graph.grf")            # or dgraph.build(...) from local CSR arrays
dgraph.build_grid_3d(8, 8, 8)       # or a synthetic 3D grid, no file needed

# Distributed partitioning / mapping: each rank gets its local part array
partloctab = dgraph.part(4)                       # SCOTCH_dgraphPart
arch = Architecture.complete_graph(4)
maploctab = dgraph.map(arch)                      # SCOTCH_dgraphMap
maploctab = dgraph.map_compute(arch)              # MapInit/MapCompute/MapExit
dgraph.map_save("out.map", arch)                  # computed + saved on root
dgraph.map_view("out.txt", arch)                  # mapping statistics on root

# Distributed ordering
permloctab = dgraph.order()                       # local slice of global perm
dordering = dgraph.order_init()                   # explicit lifecycle
dgraph.order_compute(dordering)                   # or order_compute_list(...)
permloctab = dgraph.order_perm(dordering)
cblknbr = dgraph.order_cblk_dist(dordering)
treetab, sizetab = dgraph.order_tree_dist(dordering)
dgraph.order_save(dordering, "out.ord")           # also order_save_map/_tree
dgraph.order_exit(dordering)

# Centralized <-> distributed conversion (sequential Graph on the root rank)
cgraph = Graph() if rank == 0 else None
dgraph.gather(cgraph)                             # SCOTCH_dgraphGather
dgraph2 = Dgraph()
dgraph2.scatter(cgraph)                           # SCOTCH_dgraphScatter

# Statistics and cleanup
stats = dgraph.stat()                             # SCOTCH_dgraphStat
dgraph.free()                                     # contents only; reusable
dgraph.exit()
mpi.finalize()
```

Parallel strategies are set through `Strategy`:

```python
from pyscotch import Strategy

strat = Strategy()
strat.set_dgraph_mapping("...")                  # SCOTCH_stratDgraphMap
strat.set_dgraph_ordering("...")                 # SCOTCH_stratDgraphOrder
strat.build_dgraph_mapping(0, procnbr, partnbr, 0.05)
strat.build_dgraph_ordering(0, procnbr, 0, 0.2)
strat.build_dgraph_clustering(0, procnbr, 1, 1.0, 0.05)
```

## Command-Line Interface

PyScotch provides a CLI for common operations. It is installed as the `pyscotch` command
(see `pyscotch/cli.py` for implementation details):

### Partition a Graph

```bash
pyscotch partition input.grf -n 4 -o output.map
pyscotch partition input.grf -n 8 --strategy quality
pyscotch partition input.grf -n 4 --strategy fast
```

### Order a Graph

```bash
pyscotch order input.grf -o output.ord
pyscotch order input.grf --strategy nested
pyscotch order input.grf --strategy quality
```

### Check Graph

```bash
pyscotch check input.grf
```

### Graph Info

```bash
pyscotch info input.grf
```

### Partition a Mesh

```bash
pyscotch partition input.msh -n 4 --type mesh -o output.map
```

## File Formats

### Graph Format (.grf)

Scotch graph format:
```
<version> <vertnbr> <edgenbr> <baseval> <vertflag> <edgeflag>
<vertex weights and labels>
<adjacency lists>
```

### Mapping Format (.map)

Simple format:
```
<size>
<vertex_idx> <partition_idx>
...
```

### Ordering Format (.ord)

```
<size>
<vertex_idx> <perm_val> <inverse_val>
...
```

## Examples

See the `examples/` directory for complete examples:
- `simple_partition.py` - Basic graph partitioning
- `graph_ordering.py` - Graph ordering for sparse matrices

## Error Handling

All operations may raise:
- `RuntimeError` - When Scotch operations fail
- `FileNotFoundError` - When input files don't exist
- `ValueError` - When parameters are invalid

Always check return values and handle exceptions appropriately.
