# Tutorial: Using PyScotch

This page walks through real workflows with PyScotch. Every code block below
is a standalone script that's tested as part of our CI.

## 1. Building Graphs

### From Edge Lists

The simplest way to create a graph:

{% example "ex_04_from_edges.py" %}

### From CSR Arrays

For performance or when integrating with existing code, build directly from
CSR (Compressed Sparse Row) arrays:

{% example "ex_04_from_csr.py" %}

### Loading from Files

Scotch has its own graph file format (`.grf`). You can save and load:

{% example "ex_04_save_load.py" %}

## 2. Partitioning

### Basic Partitioning

Split a graph into `k` balanced parts:

{% example "ex_04_partition_basic.py" %}

### Strategy Control

Scotch supports different partitioning strategies. The default is usually
best, but you can tune:

{% example "ex_04_strategies.py" %}

## 3. Graph Coloring

Coloring assigns colors to vertices such that no two adjacent vertices
share the same color. Useful for identifying independent sets:

{% example "ex_04_coloring.py" %}

## 4. Mesh Operations

Scotch also handles meshes (elements + nodes). You can build a mesh,
convert it to a graph, and partition:

{% example "ex_04_mesh.py" %}

## 5. File I/O Roundtrips

A common pattern: load, process, save:

{% example "ex_04_roundtrip.py" %}

## Command-Line Interface

PyScotch also provides a CLI:

```bash
# Partition a graph file into 4 parts
pyscotch partition input.grf -n 4 -o output.map

# Order a graph
pyscotch order input.grf -o output.ord

# Check graph validity
pyscotch check input.grf

# Show graph info
pyscotch info input.grf
```
