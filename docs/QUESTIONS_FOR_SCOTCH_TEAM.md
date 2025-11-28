# Questions and Observations for Scotch Team

This file tracks observations and potential issues discovered while porting Scotch C tests to Python bindings (PyScotch).

## Graph Coloring Issues (SCOTCH_graphColor)

### Issue 1: Non-deterministic and sometimes invalid colorings

**Observed during**: Porting test_scotch_graph_color.c

**Description**:
The `SCOTCH_graphColor()` function produces non-deterministic results that sometimes generate **invalid colorings** (adjacent vertices with the same color).

**Test case**: 2x2 grid graph
```
Graph structure:
0 -- 1
|    |
2 -- 3

verttab: [0, 2, 4, 6, 8]
edgetab: [1, 2, 0, 3, 0, 3, 1, 2]
```

**Observations**:
- When running `test_color_grid_2x2` **alone**: produces **valid** 3-color solution `[2, 1, 1, 0]` ✅
- When running with other tests: sometimes produces **invalid** 2-color solution `[1, 1, ?, 0]` where vertices 0 and 2 are adjacent but both have color 1 ❌

**Evidence**:
```bash
# Run alone - PASSES with 3 colors
pytest tests/scotch_ports/test_scotch_graph_color.py::TestGraphColor::test_color_grid_2x2 -v
# Output: "2x2 Grid graph: 3 colors" - VALID coloring

# Run with all tests - FAILS with 2 colors
pytest tests/scotch_ports/test_scotch_graph_color.py -v
# Output: "2x2 Grid graph: 2 colors" - INVALID coloring (vertices 0 and 2 both color 1)
```

**Questions**:
1. Is `SCOTCH_graphColor()` supposed to be deterministic?
2. Should there be a `SCOTCH_randomReset()` call before coloring operations?
3. Is there state pollution between successive `SCOTCH_graphColor()` calls?
4. Should the C test include validity checks? The current test only verifies the function returns success, but doesn't verify the coloring is valid.

**Why the C test doesn't catch this**:
The original `test_scotch_graph_color.c` only checks:
- Function returns 0 (success)
- Prints histogram of color usage

It does **NOT** verify:
- No adjacent vertices have the same color (fundamental coloring validity)
- Coloring is optimal or near-optimal

### Issue 2: Non-optimal colorings

**Description**:
Even when valid, colorings are often far from optimal.

**Examples**:
- **Path graph** (0-1-2-3): Used **4 colors** instead of optimal **2 colors**
- **Triangle** (0-1-2-0): Used **3 colors** (optimal, but it's chromatic number is 3)
- **Ring** (10 vertices): Used **3 colors** (optimal for even cycle is 2)

**Questions**:
1. Is `SCOTCH_graphColor()` intended to produce optimal colorings?
2. Is it a greedy heuristic that may produce suboptimal results?
3. Should the documentation clarify the quality guarantees?

### Issue 3: Test coverage in Scotch

**Observation**:
The C test `test_scotch_graph_color.c` has minimal validation:

```c
if (SCOTCH_graphColor (&grafdat, colotab, &colonbr, 0) != 0) {
    SCOTCH_errorPrint ("main: cannot color graph");
    exit (EXIT_FAILURE);
}

// Just prints histogram - no validity checks!
for (vertnum = 0; vertnum < vertnbr; vertnum++)
    cnbrtab[colotab[vertnum]]++;
```

**Questions**:
1. Is there a reason the test doesn't verify coloring validity?
2. Should Scotch tests include assertions that no adjacent vertices share colors?
3. Are there other graph algorithms in Scotch with similarly minimal test validation?

## Recommendations

1. **Add validity checks to C tests**: Verify basic correctness properties (e.g., valid colorings)
2. **Document algorithm behavior**: Clarify determinism, optimality guarantees, and state management
3. **Add determinism controls**: Consider `SCOTCH_randomSeed()` or `SCOTCH_randomReset()` to make coloring deterministic when needed

---

## SCOTCH_Dgraph Structure Size Issue (PT-Scotch)

### Issue: Buffer Overflow When Using Fixed-Size Opaque Structures

**Discovered**: 2025-11-28

**Description**:
We discovered that PyScotch was experiencing memory corruption, segfaults during garbage collection, and crashes after `MPI_Finalize()` when using distributed graphs (PT-Scotch). The root cause was a **buffer overflow** due to incorrect structure sizing.

### Technical Details

PyScotch originally used a fixed 256-byte buffer for all opaque Scotch structures:

```python
# pyscotch/libscotch.py (BEFORE fix)
_OPAQUE_STRUCTURE_SIZE = 256

class SCOTCH_Dgraph(Structure):
    _fields_ = [("_opaque", ctypes.c_byte * _OPAQUE_STRUCTURE_SIZE)]
```

However, examining the generated headers in `libscotch/ptscotch.h` reveals:

```c
typedef struct {
  double                    dummy[37];
} SCOTCH_Dgraph_64;

typedef struct {
  double                    dummy[15];
} SCOTCH_Graph_64;
```

**Actual sizes**:
| Structure | Doubles | Actual Size | PyScotch Allocated | Overflow |
|-----------|---------|-------------|-------------------|----------|
| `SCOTCH_Dgraph_64` | 37 | **296 bytes** | 256 bytes | **40 bytes!** |
| `SCOTCH_Graph_64` | 15 | 120 bytes | 256 bytes | None |

### Symptoms

The 40-byte buffer overflow caused:
1. **Segfaults during Python garbage collection** after MPI operations
2. **Memory corruption** in multi-level coarsening workflows
3. **Crashes after `MPI_Finalize()`** when Python tried to clean up Dgraph objects
4. **Non-deterministic failures** - sometimes tests passed, sometimes crashed

### How ScotchPy (Official Bindings) Handles This

We discovered that ScotchPy queries the structure size dynamically at runtime:

```python
# scotchpy/dgraph.py:88-91
class _DGraphStruct(ctypes.Structure):
    _fields_ = [
        ("dummy", ctypes.c_char * _common.libptscotch.SCOTCH_dgraphSizeof())
    ]
```

This is the correct approach - it calls `SCOTCH_dgraphSizeof()` to get the actual size.

### Our Fix

We increased the fixed buffer size to 512 bytes for safety:

```python
# pyscotch/libscotch.py (AFTER fix)
# CRITICAL: SCOTCH_Dgraph_64 requires 37 doubles = 296 bytes!
# We use 512 bytes for safety margin and future Scotch versions.
_OPAQUE_STRUCTURE_SIZE = 512
```

### Questions for Scotch Team

1. **Is 37 doubles (296 bytes) the maximum size for `SCOTCH_Dgraph`?** Could this grow in future versions?

2. **What are the actual sizes for all opaque structures?** We found:
   - `SCOTCH_Dgraph_64`: 37 doubles = 296 bytes
   - `SCOTCH_Graph_64`: 15 doubles = 120 bytes
   - `SCOTCH_DgraphHaloReq_64`: 3 doubles = 24 bytes

   Are there others we should be aware of?

3. **Is there a recommended approach for Python bindings?**
   - Dynamic sizing via `SCOTCH_*Sizeof()` functions (like ScotchPy does)
   - Fixed buffer with generous padding (like we do now)
   - Something else?

4. **Why are the sizes specified in doubles rather than bytes?** Is this for alignment purposes?

5. **Are the 32-bit versions smaller?** We only tested 64-bit. Should we expect:
   - `SCOTCH_Dgraph` (32-bit) to be smaller than `SCOTCH_Dgraph_64`?
   - Different dummy array sizes?

### Verification

After the fix, all 256 tests pass including:
- Multi-level distributed coarsening
- MPI cleanup without segfaults
- Proper garbage collection

```
=== Distributed Coarsening Workflow Integration Test ===

[Test 1] Single-level coarsening workflow
  Original: 9800 vertices (global), 57978 edges
  Coarsened: 5269 vertices (ratio: 0.5377)
  ✓ Single-level coarsening PASSED

[Test 2] Multi-level coarsening workflow
  Level 0: 9800 vertices
  Level 1: 5274 vertices
  Level 2: 2860 vertices
  ✓ Multi-level coarsening PASSED

[Test 3] Connectivity preservation
  ✓ Connectivity preservation PASSED

=== All Distributed Coarsening Workflow Tests PASSED ===
```

### References

- PyScotch fix: `pyscotch/libscotch.py:21-25`
- ScotchPy dynamic sizing: `scotchpy/scotchpy/dgraph.py:88-91`
- Scotch header with sizes: `libscotch/ptscotch.h`
- `SCOTCH_dgraphSizeof()` implementation: `external/scotch/src/libscotch/library_dgraph.c:82`

---

## SCOTCH_dgraphCoarsen Return Value Semantics

### Question: What is the state of `coargrafptr` when coarsening fails?

**Context**:
When `SCOTCH_dgraphCoarsen()` returns `1` (graph could not be coarsened), what is the expected state of the `coargrafptr` structure?

**From the Scotch source** (`library_dgraph_coarsen.c`):
```c
int SCOTCH_dgraphCoarsen (
  SCOTCH_Dgraph * const       finegrafptr,
  // ...
  SCOTCH_Dgraph * const       coargrafptr,
  // ...
)
{
  // Returns:
  // 0 = success (coarse graph populated)
  // 1 = could not coarsen (graph too small or already optimal)
  // 2+ = error
}
```

**Our dilemma**:
When `ret == 1`, should Python bindings:

**Option A** - Return the initialized-but-empty structure:
```python
return (coarse_graph, None)  # Caller gets a Dgraph object
```

**Option B** - Clean up and return None:
```python
lib.SCOTCH_dgraphExit(coarse_graph)
return (None, None)  # Caller gets None
```

**Questions**:

1. **When `SCOTCH_dgraphCoarsen` returns 1, is `coargrafptr` in a valid state?**
   - Was `SCOTCH_dgraphInit` called on it internally?
   - Does it need `SCOTCH_dgraphExit` to be called?
   - Or is it untouched/uninitialized?

2. **What does the Scotch test suite do?**
   - Looking at `test_scotch_dgraph_coarsen.c`, it doesn't seem to test the "cannot coarsen" case explicitly.

3. **What is the recommended pattern for bindings?**
   - Should we always call `SCOTCH_dgraphExit` on `coargrafptr` regardless of return value?
   - Or only when `ret == 0`?

**Why this matters**:
- If we don't clean up when needed → memory leak
- If we clean up when not needed → potential double-free or invalid state
- Changing return semantics (`Dgraph` vs `None`) affects user code

**Note**: We initially changed the return to `(None, None)` and added defensive null checks throughout the test workflows. We've reverted these changes pending clarification, as they weren't the root cause of our issues (the buffer overflow was).

---

## References

- Original C test: `external/scotch/src/check/test_scotch_graph_color.c`
- Python port: `tests/scotch_ports/test_scotch_graph_color.py`
- PyScotch binding: `pyscotch/graph.py:355` (color method)
- Debug evidence: See commit history for detailed test output showing invalid colorings

---

**Created**: 2025-11-12
**Last updated**: 2025-11-28
