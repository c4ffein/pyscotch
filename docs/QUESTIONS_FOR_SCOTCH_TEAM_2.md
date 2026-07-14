# Questions for Scotch Team - Round 2

New issues discovered via Hypothesis property-based testing.

---

## SCOTCH_graphColor Bug with Sparse Graphs — RESOLVED in v7.0.11 (see [COLORING_BUG_RESOLUTION.md](COLORING_BUG_RESOLUTION.md))

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

**Update 2026-03-25**: Fixed upstream — see [COLORING_BUG_RESOLUTION.md](COLORING_BUG_RESOLUTION.md) for the full timeline.

---

*Created: 2025-12-05*
*Test file: tests/hypothesis/test_graph_properties.py*

---

## SCOTCH_memFree is exported without the _32/_64 suffix despite SCOTCH_RENAME_ALL

*Added: 2026-07-12, found by tests/pyscotch_base/test_binding_signatures.py*

When Scotch v7.0.11 is built with `-DSCOTCH_NAME_SUFFIX=_64 -DSCOTCH_RENAME_ALL`,
the generated `scotch.h` declares `SCOTCH_memFree_64`, but the shared library
exports the **unsuffixed** symbol:

```
$ grep memFree scotch-builds/inc64/scotch.h
void  SCOTCH_memFree_64  (void * const);
$ nm -D scotch-builds/lib64/libscotch.so | grep memFree
00000000000648f0 T SCOTCH_memFree
```

Neighboring functions (`SCOTCH_memCur_64`, `SCOTCH_memMax_64`) are suffixed
correctly, so `SCOTCH_memFree` appears to be missing from the rename machinery.
Any C program compiled against the suffixed header and calling
`SCOTCH_memFree` will fail to link. Since the function is int-size independent
this is harmless for PyScotch (we special-case it and resolve the unsuffixed
symbol), but the header/library mismatch looks unintended.

---

## v7.0.12 does not build with SCOTCH_RENAME_ALL: SCOTCH_meshBuildElem missing from module.h

*Added: 2026-07-12, found while validating PyScotch against v7.0.12*

The new public function `SCOTCH_meshBuildElem` (added in v7.0.12 by commit
2285ed4 "Refactor `_SCOTCH_METIS_MeshToDual2()` as `SCOTCH_meshBuildElem()`")
has no entry in `src/libscotch/module.h`'s rename table. With
`-DSCOTCH_NAME_SUFFIX=_64 -DSCOTCH_RENAME_ALL` the build **fails**:

```
library_mesh_f.c:233:14: error: implicit declaration of function
'SCOTCH_meshBuildElem'; did you mean 'SCOTCH_meshBuildElem_64'?
```

(`library_mesh_f.c` calls the unsuffixed name; the generated `scotch.h`
declares only the suffixed one, and implicit declarations are errors with
current GCC.)

This is the same root cause as the `SCOTCH_memFree` issue above: both names
are missing from module.h's `SCOTCH_NAME_PUBLIC` list. Two-line fix, verified
against PyScotch's full test suite (all 4 variants pass with v7.0.12 once
applied): see `patches/scotch-7.0.12-rename-all-fix.patch` in this repo.

---

## SCOTCH_contextOptionSetNum switches on the option *value* instead of the option *index*

*Added: 2026-07-12, found while writing behavioral tests for context options*

In `library_context.c` (v7.0.11), `SCOTCH_contextOptionSetNum()` contains:

```c
switch (optival) {                                /* <-- should be optinum? */
  case CONTEXTOPTIONNUMRANDOMFIXEDSEED :
    if (optitmp != 0)
      optitmp = 1;                                /* Only two values available */
    break;
  case CONTEXTOPTIONNUMDETERMINISTIC :
    if (optitmp != 0) {
      optitmp = 1;
      o = contextValuesSetInt ((Context *) libcontptr, CONTEXTOPTIONNUMRANDOMFIXEDSEED, 1);
    }
    break;
  default :
    errorPrint (STRINGIFY (SCOTCH_contextOptionSetNum) ": invalid option name");
    return (1);
}
```

The `switch` is on `optival` (the value being set) rather than on `optinum`
(the option index). Since `CONTEXTOPTIONNUMDETERMINISTIC == 0` and
`CONTEXTOPTIONNUMRANDOMFIXEDSEED == 1`, the dispatch accidentally "works" for
values 0 and 1, but the observable consequences are:

1. **The documented cascade never happens.** Setting
   `SCOTCH_OPTIONNUMDETERMINISTIC` to 1 is supposed to also force
   `SCOTCH_OPTIONNUMRANDOMFIXEDSEED` to 1 ("If deterministic behavior wanted,
   use fixed random seed"), but the value 1 lands in the
   `CONTEXTOPTIONNUMRANDOMFIXEDSEED` case, which only clamps. Reproduction:

   ```python
   ctx = Context()
   ctx.option_set(1, 0)   # RANDOMFIXEDSEED off
   ctx.option_set(0, 1)   # DETERMINISTIC on
   ctx.option_get(1)      # -> 0, expected 1 per the code's intent
   ```

2. **Values >= 2 are rejected instead of clamped.** The `if (optitmp != 0)
   optitmp = 1;` clamping code is unreachable for any value other than 0/1:
   e.g. `SCOTCH_contextOptionSetNum(ctx, SCOTCH_OPTIONNUMDETERMINISTIC, 2)`
   falls into `default:` and fails with "invalid option name" even though the
   option name is valid.

3. **Invalid option indices are only caught late.** E.g. option index 99 with
   value 1 is dispatched as if it were a fixed-seed update, and only fails in
   `contextValuesSetInt()`'s bounds check.

Our tests only assert the 0/1 round-trip behavior, which is identical whether
or not the `switch` is fixed; we did not encode the cascade or the clamping
in tests since both look unintended in their current form.

### Question

Should this be `switch (optinum)`? If so, is the cascading of
DETERMINISTIC=1 into RANDOMFIXEDSEED=1 the intended long-term semantics
(i.e., should PyScotch expose/emulate it)?

---

## Public functions declared in scotch.h but documented in neither user manual

*Added: 2026-07-13, found while generating deep links from the PyScotch API
reference into the user manuals (function → page map extracted from the PDFs'
own bookmarks).*

Of the 149 public functions PyScotch binds, 8 appear in `scotch.h` /
`ptscotch.h` (v7.0.11) but in neither `scotch_user7.0.pdf` nor
`ptscotch_user7.0.pdf`:

- `SCOTCH_archBuild` (the manual documents `SCOTCH_archBuild0`/`archBuild2`,
  but not the plain `archBuild` also exported)
- `SCOTCH_archVar`
- `SCOTCH_graphGeomLoadMmkt` / `SCOTCH_graphGeomSaveMmkt` (Matrix Market
  geometry I/O; the other Geom formats are documented)
- `SCOTCH_graphOrderList`
- `SCOTCH_graphPartOvlView`
- `SCOTCH_randomSave` / `SCOTCH_randomLoad`

Is the omission intentional (semi-private API)? If so, a note in the headers
would help binding authors; if not, this list may help complete the manuals.

---

## Rename-table sweep: SCOTCH_contextAlloc is also missing from module.h

*Added: 2026-07-13, from a mechanical sweep of library.h vs module.h*

Cross-checking every public function in `library.h` against `module.h`'s
`SCOTCH_NAME_PUBLIC` rename table (v7.0.11 and v7.0.12) finds 5 absentees:
`SCOTCH_memFree` (reported above), `SCOTCH_meshBuildElem` (7.0.12, reported
above), **`SCOTCH_contextAlloc`** (exports unsuffixed while e.g.
`SCOTCH_graphAlloc_64` is correctly suffixed — verified with `nm`), and
`SCOTCH_errorPrint`/`SCOTCH_errorPrintW`/`SCOTCH_errorProg` (possibly
intentional, since the error library is shared between suffixed variants —
if so, a comment in module.h would make that explicit).

The sweep is a 15-line script; happy to contribute it as a CI check upstream
so this bug class cannot recur.

---

## libscotch.so under-declares its shared-library dependencies (no NEEDED for libz/libm/libpthread)

*Added: 2026-07-14, found while building self-contained binary wheels.*

`libscotch.so` calls into zlib (`gzread`, `gzclose`, …), libm, and libpthread,
but its dynamic section records `NEEDED = libc.so.6` only — the other
dependencies are undeclared:

```
$ nm -D scotch-builds/lib64/libscotch.so | grep -E ' U (gz|pthread_create|sqrt)'
                 U gzclose
                 U gzread
                 U pthread_create@...
$ readelf -d scotch-builds/lib64/libscotch.so | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so.6]     # libz/libm/libpthread absent
```

Root cause is in `src/Makefile.inc`: the shared object is created with
`AR = gcc`, `ARFLAGS = -shared -o` (i.e. `gcc -shared -o libscotch.so *.o`),
while `LDFLAGS = -lz -lm -lrt -pthread ...` is applied only when linking the
command-line executables. So the libraries never make it into the `.so`'s own
`NEEDED` list.

This is invisible in normal use — Scotch's executables supply the libraries at
their final link, and most distro packages re-link the shared object with
proper `NEEDED` — so it has clearly never caused a problem in practice. It only
surfaces when the *bare, as-built* `.so` is loaded standalone (e.g. `dlopen`'d
by a language binding) under eager binding: the manylinux toolchain links with
`-z now`, so the loader resolves every symbol up front and the import fails with

```
libscotch.so: undefined symbol: gzclose
```

Under the more common lazy binding it "works" until the first compressed-file
operation, which makes it a latent trap rather than an immediate error.

### Suggested fix (upstream)

Link the shared object with its libraries, or — cleaner — build it with
`-Wl,--no-undefined`, which makes the linker **reject** an under-declared shared
object at build time instead of silently shipping one. Either way the `.so`
becomes self-describing and every downstream that loads it directly benefits.

### Question

Is the shared library intentionally built to defer its library resolution to
the executable link, or would recording the real `NEEDED` entries (and/or adding
`-Wl,--no-undefined` as a guardrail) be a welcome change? We're happy to send a
small Makefile.inc patch if useful.

### What PyScotch does meanwhile

Two independent, self-sufficient layers (see
`scripts/build_wheel_libs.sh` step 3b and `pyscotch/libscotch.py`
`_preload_dependencies`): we stamp the honest `NEEDED` entries onto the bundled
wheel library with `patchelf`, and we also preload the dependency by runtime
soname (`libz.so.1`) before Scotch loads — the latter also covers an
under-linked *system* Scotch, which we cannot re-link.
