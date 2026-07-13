# Coarsening and Partitioning

## The Problem: Splitting a Graph

Imagine you have a mesh with 10 million cells and 128 processors.
You need to assign cells to processors such that:

1. Each processor gets roughly the same number of cells (**load balance**)
2. The number of edges between processors is minimized (**communication cost**)

This is the **graph partitioning problem**, and it's NP-hard. You can't brute-force it.

## The Multilevel Approach

Scotch (and most modern partitioners) use a **multilevel** strategy:

<figure class="diagram">
<svg width="680" height="292" viewBox="0 0 680 292" role="img" aria-label="The multilevel V-cycle: the graph is coarsened from 10 million down to 10 thousand vertices, partitioned quickly at the coarsest level, then uncoarsened and refined back up to a good-quality partition of the original graph">
  <defs>
    <marker id="vc-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L8,4 L0,8 z" fill="#6b6b6b"/>
    </marker>
    <marker id="vc-arrow-accent" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L8,4 L0,8 z" fill="#c83232"/>
    </marker>
  </defs>

  <!-- descent: coarsening -->
  <g fill="none" stroke="#6b6b6b" stroke-width="1.5">
    <line x1="122" y1="68" x2="156" y2="106" marker-end="url(#vc-arrow)"/>
    <line x1="162" y1="162" x2="196" y2="200" marker-end="url(#vc-arrow)"/>
  </g>
  <!-- ascent: refinement -->
  <g fill="none" stroke="#6b6b6b" stroke-width="1.5">
    <line x1="518" y1="200" x2="552" y2="162" marker-end="url(#vc-arrow)"/>
    <line x1="558" y1="106" x2="592" y2="68" marker-end="url(#vc-arrow)"/>
  </g>
  <!-- the fast partition at the bottom of the V -->
  <line x1="304" y1="228" x2="356" y2="228" fill="none" stroke="#c83232" stroke-width="2" marker-end="url(#vc-arrow-accent)"/>

  <g font-family="Inter, sans-serif" text-anchor="middle">
    <!-- left column: coarsening -->
    <rect x="20" y="16" width="200" height="48" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="120" y="36" font-size="13" font-weight="600" fill="#1c1c1c">Original graph</text>
    <text x="120" y="53" font-size="11.5" fill="#6b6b6b">10M vertices</text>

    <rect x="60" y="110" width="200" height="48" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="160" y="130" font-size="13" font-weight="600" fill="#1c1c1c">Coarser graph</text>
    <text x="160" y="147" font-size="11.5" fill="#6b6b6b">1M vertices</text>

    <rect x="100" y="204" width="200" height="48" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="200" y="224" font-size="13" font-weight="600" fill="#1c1c1c">Coarsest graph</text>
    <text x="200" y="241" font-size="11.5" fill="#6b6b6b">10K vertices</text>

    <!-- right column: uncoarsening -->
    <rect x="360" y="204" width="200" height="48" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="460" y="224" font-size="13" font-weight="600" fill="#1c1c1c">Coarsest partition</text>
    <text x="460" y="241" font-size="11.5" fill="#6b6b6b">computed in no time</text>

    <rect x="400" y="110" width="200" height="48" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="500" y="130" font-size="13" font-weight="600" fill="#1c1c1c">Finer partition</text>
    <text x="500" y="147" font-size="11.5" fill="#6b6b6b">projected + refined</text>

    <rect x="440" y="16" width="200" height="48" rx="8" fill="#fdf5f5" stroke="#c83232"/>
    <text x="540" y="36" font-size="13" font-weight="600" fill="#1c1c1c">Final partition</text>
    <text x="540" y="53" font-size="11.5" fill="#6b6b6b">good quality!</text>

    <!-- edge labels -->
    <text x="122" y="95" font-size="11.5" fill="#6b6b6b" text-anchor="end">coarsen</text>
    <text x="162" y="189" font-size="11.5" fill="#6b6b6b" text-anchor="end">coarsen</text>
    <text x="558" y="189" font-size="11.5" fill="#6b6b6b" text-anchor="start">uncoarsen + refine</text>
    <text x="598" y="95" font-size="11.5" fill="#6b6b6b" text-anchor="start">refine</text>
    <text x="330" y="275" font-size="11.5" fill="#1c1c1c" font-weight="500">partition</text>
    <text x="330" y="289" font-size="10.5" fill="#6b6b6b">(fast — it&#8217;s small!)</text>
  </g>
</svg>
</figure>

### Step 1: Coarsening

**Coarsening** merges pairs of adjacent vertices into single "super-vertices".
Each round roughly halves the graph. The key insight: a good partition of the
coarse graph is a good starting point for the fine graph.

{% example "ex_02_coarsen.py" %}

### Step 2: Partition the Coarsest Level

When the graph is small enough, even a simple algorithm produces decent results.
Scotch uses recursive bisection or k-way partitioning.

### Step 3: Uncoarsen and Refine

Project the partition back to finer levels. At each level, run a local refinement
algorithm (like Fiduccia-Mattheyses) to improve boundary vertices.

## Partitioning in Practice

With PyScotch, you don't need to manage the multilevel process yourself.
The `partition()` call handles everything:

{% example "ex_02_partition.py" %}

## Ordering

Graph ordering rearranges vertices to reduce **fill-in** during sparse matrix
factorization (LU, Cholesky). Scotch uses **nested dissection**: recursively
find a small separator that splits the graph in two, then order each half
independently. The separator vertices go last.

This produces orderings where the factored matrix has far fewer nonzeros
than the original.

{% example "ex_02_ordering.py" %}
