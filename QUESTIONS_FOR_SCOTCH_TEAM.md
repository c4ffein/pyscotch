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

## References

- Original C test: `external/scotch/src/check/test_scotch_graph_color.c`
- Python port: `tests/scotch_ports/test_scotch_graph_color.py`
- PyScotch binding: `pyscotch/graph.py:355` (color method)
- Debug evidence: See commit history for detailed test output showing invalid colorings

---

**Created**: 2025-11-12
**Last updated**: 2025-11-16
