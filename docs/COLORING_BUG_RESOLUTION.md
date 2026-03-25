# SCOTCH_graphColor Bug — Resolution

Resolved in Scotch v7.0.11 (commit `e0a90c7`, January 15 2026).

For the original bug report, reproduction, and source analysis, see [QUESTIONS_FOR_SCOTCH_TEAM_2.md](QUESTIONS_FOR_SCOTCH_TEAM_2.md).

## Timeline

- **2025-12-05**: PyScotch's Hypothesis property-based tests (written by Claude, directed by @c4ffein) discover that `SCOTCH_graphColor()` produces invalid colorings on sparse graphs — adjacent vertices assigned the same color. The bug is documented with a detailed root cause analysis of `library_graph_color.c` and the test is marked `xfail`.

- **2026-01-14**: Scotch adds a coloring-checking routine in `test_scotch_graph_color.c` (commit `34ea137`).

- **2026-01-15**: Scotch fixes the bug in commit `e0a90c7` — "Bugfix: sequential coloring now considers neighbors colored in same pass".

- **2026-03-25**: We update to Scotch v7.0.11, remove the `xfail` marker, and confirm the test passes.

## Our analysis was correct

In December 2025, we identified the issue at line 145 of the original `library_graph_color.c`:

```c
if (colotax[vertend] >= 0)
    continue;  // Skip already-colored neighbors
```

This skipped *all* colored neighbors, including those colored in the *current* pass. Two adjacent vertices could both "win" their independent-set check in the same pass.

The upstream fix confirms this exactly:

```c
coloend = colotax[vertend];

if ((coloend >= 0) &&        // If vertex has been colored
    (coloend < colonum))     // In a former pass
    continue;                // Do not consider it any longer
```

The added `coloend < colonum` condition ensures neighbors colored in the current pass are still considered as competitors.

## Why property-based testing matters

Scotch's own C tests only verified return codes and printed histograms — they did not check that the coloring was actually valid. The checking routine was added the day before the fix.

Our Hypothesis test checked the fundamental invariant for *all* valid graphs and found the counterexample automatically:

```python
@given(graph_data=simple_graph(min_vertices=2, max_vertices=20))
def test_coloring_no_adjacent_same_color(self, graph_data):
    num_vertices, edges = graph_data
    graph = Graph.from_edges(edges, num_vertices=num_vertices)
    coloring, num_colors = graph.color()

    for u, v in edges:
        assert coloring[u] != coloring[v]
```

---

*Created: 2026-03-25*
*Original report: 2025-12-05*
*Test file: tests/hypothesis/test_graph_properties.py*
