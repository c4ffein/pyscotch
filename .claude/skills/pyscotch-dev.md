---
name: pyscotch-dev
description: PyScotch development guide - Scotch API patterns, common pitfalls, testing conventions
---

# PyScotch Development Guide

You are working on PyScotch, a Python ctypes wrapper for the PT-Scotch graph partitioning library.

## Project Setup

- Use `uv` for package management (not `pip`)
- Initialize submodule: `git submodule update --init --recursive`
- Build Scotch: `make build-all`
- Run tests: `PYSCOTCH_INT_SIZE=64 PYSCOTCH_PARALLEL=0 python -m pytest tests/`
- Install in dev mode: `uv pip install -e .`

## Environment Variables

- `PYSCOTCH_INT_SIZE`: `32` or `64` (default: `64`) - controls Scotch integer width
- `PYSCOTCH_PARALLEL`: `0` or `1` (default: `0`) - `1` loads PT-Scotch (MPI variant)

## Scotch API Patterns

### Resource Management
All Scotch structures support context managers:
```python
with Graph() as g:
    g.build(verttab, edgetab)
    # ... use graph
# g.close() called automatically
```

### Random State
**Always call `random_reset()` before randomized operations** (partitioning, coloring, ordering).
Without it, the PRNG state carries over between calls, producing non-deterministic results.

### Error Codes
- `0` = success
- `1` = operation not possible (e.g., graph too small to coarsen) — **not an error**, but output may be invalid
- `2+` = actual error

### Structure Sizing
Always use `SCOTCH_*Sizeof()` for structure sizes. Never hardcode — sizes differ between 32-bit and 64-bit variants.

### Coarsening Gotcha
When `SCOTCH_dgraphCoarsen` returns 1 (cannot coarsen), the coarse graph is in an **invalid state**.
Do NOT call `SCOTCH_dgraphExit` on it. Mark `_exit_called = True` to prevent cleanup.

### FILE* I/O
Use the `c_fopen()` context manager from `pyscotch.graph` for all Scotch file operations:
```python
from pyscotch.graph import c_fopen
with c_fopen("graph.grf", "r") as fp:
    lib.SCOTCH_graphLoad(byref(graph._graph), fp, -1, 0)
```

## Testing Conventions

- **Never modify tests to make them pass.** Fix the implementation instead.
- When porting C tests, maximize similarity with the original.
- If a test seems incomplete, add notes to `QUESTIONS_FOR_SCOTCH_TEAM.md`.
- Scotch's C tests often only check return codes — our tests should verify output validity too.
- Call `random_reset()` in tests for deterministic results.
- Doc examples in `docs/site/examples/` are also tested via pytest.

## Key Files

| File | Purpose |
|------|---------|
| `pyscotch/libscotch.py` | ctypes bindings, library loading |
| `pyscotch/graph.py` | Graph class + `c_fopen` shim |
| `pyscotch/dgraph.py` | Distributed graph (MPI) |
| `pyscotch/mesh.py` | Mesh operations |
| `pyscotch/strategy.py` | Strategy strings and presets |
| `tests/scotch_ports/` | Ported C test suite |
| `tests/pyscotch_base/` | PyScotch-specific tests |
| `docs/site/examples/` | Tested documentation examples |
