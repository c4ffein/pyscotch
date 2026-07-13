# What's PyScotch?

## Scotch: The C Library

[PT-Scotch](https://gitlab.inria.fr/scotch/scotch) is a graph partitioning library
developed at INRIA Bordeaux. It's been around since the 1990s, is battle-tested in
production HPC codes, and supports both sequential and distributed (MPI) operations.

The "PT" stands for "Parallel Threaded" — the distributed variant that runs
across multiple MPI processes.

## PyScotch: Python Bindings via ctypes

PyScotch wraps PT-Scotch's C API using Python's `ctypes` module. No Cython, no
C extensions, no mpi4py dependency. This keeps the build simple and the dependency
surface small.

### Key Design Decisions

**Multi-variant loading.** PyScotch can load 4 different Scotch builds:

| Variant | `PYSCOTCH_INT_SIZE` | `PYSCOTCH_PARALLEL` |
|---------|---------------------|---------------------|
| 32-bit sequential | `32` | `0` |
| 64-bit sequential | `64` | `0` |
| 32-bit parallel | `32` | `1` |
| 64-bit parallel | `64` | `1` |

Set environment variables before importing:

```python
# For 64-bit sequential (the default):
export PYSCOTCH_INT_SIZE=64
export PYSCOTCH_PARALLEL=0
```

**Dynamic structure sizing.** Scotch's opaque structs differ in size between
32-bit and 64-bit builds. PyScotch queries sizes at runtime via `SCOTCH_*Sizeof()`
functions — never hardcoded.

**FILE\* compatibility shim.** Scotch's load/save functions expect C `FILE*`
pointers. Python 3 can't produce these safely via ctypes. PyScotch includes a
small C shim (`libpyscotch_compat.so`) compiled with the same toolchain as
Scotch, providing `pyscotch_fopen()` / `pyscotch_fclose()` with guaranteed
ABI compatibility.

**Context managers for resource safety.** All Scotch structures (`Graph`, `Mesh`,
`Strategy`, `Architecture`, etc.) support Python's `with` statement:

{% example "ex_03_context_manager.py" %}

## Architecture Overview

<figure class="diagram">
<svg width="640" height="336" viewBox="0 0 640 336" role="img" aria-label="PyScotch architecture: your Python code calls the high-level API modules, which sit on libscotch.py's ctypes bindings plus the MPI wrapper and FILE* shim, all loading the Scotch and PT-Scotch C libraries">
  <defs>
    <marker id="arch-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L8,4 L0,8 z" fill="#6b6b6b"/>
    </marker>
  </defs>

  <g fill="none" stroke="#6b6b6b" stroke-width="1.5">
    <line x1="320" y1="58" x2="320" y2="72" marker-end="url(#arch-arrow)"/>
    <line x1="320" y1="160" x2="320" y2="174" marker-end="url(#arch-arrow)"/>
    <line x1="320" y1="256" x2="320" y2="270" marker-end="url(#arch-arrow)"/>
  </g>

  <g text-anchor="middle">
    <rect x="20" y="14" width="600" height="42" rx="8" fill="#fcfcfc" stroke="#d1d9e0" stroke-dasharray="5 4"/>
    <text x="320" y="40" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="#1c1c1c">Your Python code</text>

    <rect x="20" y="74" width="600" height="84" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="320" y="98" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="#1c1c1c">High-level API</text>
    <text x="320" y="120" font-family="'JetBrains Mono', monospace" font-size="11.5" fill="#6b6b6b">graph.py &#183; mesh.py &#183; dgraph.py &#183; strategy.py &#183; arch.py</text>
    <text x="320" y="140" font-family="'JetBrains Mono', monospace" font-size="11.5" fill="#6b6b6b">mapping.py &#183; ordering.py &#183; context.py &#183; geom.py &#183; cli.py</text>

    <rect x="20" y="176" width="300" height="78" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="170" y="204" font-family="'JetBrains Mono', monospace" font-size="12.5" font-weight="600" fill="#1c1c1c">libscotch.py</text>
    <text x="170" y="226" font-family="Inter, sans-serif" font-size="11" fill="#6b6b6b">ctypes bindings &#183; variant loading</text>
    <text x="170" y="241" font-family="Inter, sans-serif" font-size="11" fill="#6b6b6b">dynamic struct sizing</text>

    <rect x="330" y="176" width="140" height="78" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="400" y="208" font-family="'JetBrains Mono', monospace" font-size="12.5" font-weight="600" fill="#1c1c1c">mpi.py</text>
    <text x="400" y="230" font-family="Inter, sans-serif" font-size="11" fill="#6b6b6b">MPI, without mpi4py</text>

    <rect x="480" y="176" width="140" height="78" rx="8" fill="#ffffff" stroke="#d1d9e0"/>
    <text x="550" y="208" font-family="'JetBrains Mono', monospace" font-size="12.5" font-weight="600" fill="#1c1c1c">file_compat.c</text>
    <text x="550" y="230" font-family="Inter, sans-serif" font-size="11" fill="#6b6b6b">FILE* ABI shim</text>

    <rect x="20" y="272" width="600" height="52" rx="8" fill="#1c1c1c"/>
    <text x="320" y="294" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="#ffffff">Scotch / PT-Scotch</text>
    <text x="320" y="312" font-family="Inter, sans-serif" font-size="11" fill="#b8b8b8">C libraries &#183; 32/64-bit &#183; sequential + parallel &#183; bundled, built, or system</text>
  </g>
</svg>
</figure>

## Quick API Tour

{% example "ex_03_api_tour.py" %}
