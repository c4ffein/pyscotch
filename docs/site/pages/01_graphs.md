# What's a Graph?

Before diving into PyScotch, let's build intuition about the data structure at the heart of everything: **graphs**.

## Vertices and Edges

A graph is a collection of **vertices** (also called nodes) connected by **edges**. That's it.

- A social network: people are vertices, friendships are edges
- A road map: intersections are vertices, roads are edges
- A mesh for physics simulation: cells are vertices, shared faces are edges

In code, the most common way to represent a graph is **CSR format** (Compressed Sparse Row). Instead of storing every pair `(u, v)`, you store:

- `verttab`: for each vertex, the index where its neighbors start in the edge array
- `edgetab`: a flat array of all neighbor indices

## A Simple Example

Here's a triangle (3 vertices, each connected to the other two):

<figure class="diagram">
<svg width="200" height="168" viewBox="0 0 200 168" role="img" aria-label="A triangle graph: vertices 0, 1 and 2, each connected to the other two">
  <g stroke="#9a9a9a" stroke-width="1.5">
    <line x1="100" y1="38" x2="52" y2="126"/>
    <line x1="100" y1="38" x2="148" y2="126"/>
    <line x1="52" y1="126" x2="148" y2="126"/>
  </g>
  <g font-family="'JetBrains Mono', monospace" font-size="13" text-anchor="middle" fill="#1c1c1c">
    <circle cx="100" cy="38" r="17" fill="#ffffff" stroke="#1c1c1c" stroke-width="1.5"/>
    <text x="100" y="42.5">0</text>
    <circle cx="52" cy="126" r="17" fill="#ffffff" stroke="#1c1c1c" stroke-width="1.5"/>
    <text x="52" y="130.5">1</text>
    <circle cx="148" cy="126" r="17" fill="#ffffff" stroke="#1c1c1c" stroke-width="1.5"/>
    <text x="148" y="130.5">2</text>
  </g>
</svg>
</figure>

{% example "ex_01_triangle.py" %}

The `verttab` array has one entry per vertex plus a sentinel at the end.
Vertex 0's neighbors start at index `verttab[0] = 0` and end before `verttab[1] = 2`,
so its neighbors are `edgetab[0:2] = [1, 2]`.

## Why Graphs Matter for HPC

In high-performance computing, graphs appear everywhere:

- **Sparse matrices** are graphs: rows are vertices, nonzero entries are edges
- **Finite element meshes** have a dual graph structure
- **Task dependency DAGs** determine parallel execution order

The key operations that Scotch provides are all about *rearranging* these graphs:

| Operation | What it does | Why you'd want it |
|-----------|-------------|-------------------|
| **Partitioning** | Split vertices into balanced groups | Distribute work across processors |
| **Ordering** | Reorder vertices | Reduce fill-in during matrix factorization |
| **Coloring** | Assign colors so no neighbors share a color | Identify independent sets for parallelism |
| **Coarsening** | Merge vertices to make a smaller graph | Multilevel algorithms |

The next page dives into coarsening and partitioning — the core of what Scotch does.
