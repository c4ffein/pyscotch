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

# Default strategy
strategy = Strategy()

# Set mapping strategy
strategy.set_mapping_default()
strategy.set_recursive_bisection()
strategy.set_multilevel()

# Set ordering strategy
strategy.set_ordering_default()
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

## Command-Line Interface

> ⚠️ **NOT YET IMPLEMENTED** - The CLI described below is planned but not yet available in v0.1.0.
> For now, use the Python API directly. CLI implementation is tracked in the project roadmap.

PyScotch will provide a CLI for common operations:

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
