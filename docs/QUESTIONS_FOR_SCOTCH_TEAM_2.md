# Questions for Scotch Team - Round 2

New issues discovered via Hypothesis property-based testing.

---

## SCOTCH_graphColor Bug with Sparse Graphs

### Issue: Invalid coloring when vertex 0 is isolated and edge connects to last vertex

**Discovered**: 2025-12-05 via Hypothesis testing

**Description**:
`SCOTCH_graphColor()` returns invalid colorings (adjacent vertices with same color) under specific conditions, even with `SCOTCH_randomReset()` called beforehand.

### Reproduction

```python
from pyscotch import Graph

# This produces INVALID coloring (both vertices get color 0)
graph = Graph.from_edges([(1, 10)], num_vertices=11)
coloring, num_colors = graph.color()
# Result: num_colors=1, coloring[1]==coloring[10]==0
# BUG: Adjacent vertices have same color!

# This works correctly
graph = Graph.from_edges([(0, 10)], num_vertices=11)
coloring, num_colors = graph.color()
# Result: num_colors=2, coloring[0]!=coloring[10]
# OK: Different colors
```

### Pattern Analysis

| Condition | Result |
|-----------|--------|
| Vertex 0 is isolated + edge involves last vertex (n-1) | **BUG** - returns 1 color |
| Vertex 0 is connected | OK |
| Edge does not involve last vertex | OK |

**Systematic testing:**
```
n= 3, edge (1, 2): colors=2, OK
n= 4, edge (1, 3): colors=2, OK
...
n=10, edge (1, 9): colors=2, OK
n=11, edge (1,10): colors=1, BUG  <-- starts here
n=12, edge (1,11): colors=1, BUG
n=13, edge (1,12): colors=2, OK   <-- stops here
n=14, edge (1,13): colors=2, OK

With 11 vertices, different edges:
  edge (0,10): colors=2, OK   <-- vertex 0 connected
  edge (1,10): colors=1, BUG  <-- vertex 0 isolated, edge to last
  edge (2,10): colors=1, BUG  <-- vertex 0 isolated, edge to last
  edge (5,10): colors=1, BUG  <-- vertex 0 isolated, edge to last
  edge (0,5):  colors=2, OK   <-- vertex 0 connected
  edge (1,5):  colors=2, OK   <-- edge not to last vertex
```

### Questions

1. Is this a known limitation of `SCOTCH_graphColor()`?

2. Is there something special about vertex 0 in the coloring algorithm? (Starting point for traversal?)

3. Why does the bug appear only at specific graph sizes (11-12 vertices but not 10 or 13)?

4. Is there a workaround we should implement in Python bindings?

### Notes

- Bug is **deterministic** after `SCOTCH_randomReset()` - not a PRNG issue
- Bug only occurs with very sparse graphs (single edge, many isolated vertices)
- The algorithm returns `num_colors=1` which is mathematically impossible for a graph with any edge

### How We Found It

Hypothesis property-based test checking the invariant "no adjacent vertices share a color":

```python
@given(graph_data=simple_graph(min_vertices=2, max_vertices=20))
def test_coloring_no_adjacent_same_color(self, graph_data):
    num_vertices, edges = graph_data
    graph = Graph.from_edges(edges, num_vertices=num_vertices)
    coloring, num_colors = graph.color()

    for u, v in edges:
        assert coloring[u] != coloring[v], \
            f"Adjacent vertices {u} and {v} have same color {coloring[u]}"
```

### Source Code Analysis

We examined `library_graph_color.c` (lines 76-170). The algorithm:

1. **Initialize** all colors to -1 (uncolored)
2. **Assign random priority** to each vertex via `contextIntRandVal(..., 32768)`
3. **Iteratively find independent sets:**
   - For each uncolored vertex, check if it "wins" against all uncolored neighbors
   - Win condition (line 149-150):
     ```c
     if ((randend > randval) ||
         ((randend == randval) && (vertend > vertnum)))
       break;  // Lose - neighbor has priority
     ```
   - Winners get current color, losers go back in queue

**Tie-breaking rule:** When random values are equal, **lower vertex number wins**.

**Hypothesis for the bug:**

After `SCOTCH_randomReset()`, `contextIntRandVal` may return identical (or poorly distributed) values for all vertices. This triggers tie-breaking by vertex number exclusively:

- Vertex 0 (isolated, no neighbors) → immediately gets color 0
- Vertex 1 vs Vertex 10 (edge between them): 1 < 10, so vertex 1 "wins"
- But the check only runs for vertex 1's perspective. When we later process vertex 10, it checks vertex 1... but vertex 1 might already be colored, so the `colotax[vertend] >= 0` check (line 145) skips it?

There may be a logic issue where:
- An uncolored vertex can "win" against an already-colored neighbor (which shouldn't count)
- Or the queue management doesn't properly re-queue vertices that lost

**The algorithm should work for disconnected graphs** (it iterates all vertices), so the bug is likely in the win/lose logic or queue handling, not connectivity.

### Current Workaround

Test marked as `xfail` (expected failure) in PyScotch:
```python
@pytest.mark.xfail(reason="Upstream Scotch bug with sparse graphs - see docs/QUESTIONS_FOR_SCOTCH_TEAM_2.md")
def test_coloring_no_adjacent_same_color(self, graph_data):
    ...
```

When this is fixed upstream, the test will become `XPASS` and we'll know to remove the marker.

---

*Created: 2025-12-05*
*Test file: tests/hypothesis/test_graph_properties.py*
