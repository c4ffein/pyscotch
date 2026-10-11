# Library interface (sequential) — Scotch v7.0.11

Analyst territory: sequential public API layer, `src/libscotch/library_*.c`
excluding `library_dgraph*`, `library_dorder*`, `library_dmapping*`.
All paths below are relative to `/home/dev/workspace/pyscotch/external/scotch/src/libscotch/`
unless stated otherwise.

## Scope

- 83 files, 15,179 LOC total. Roughly half are Fortran stub files (`library_*_f.c`)
  that wrap the C API via the `SCOTCH_FORTRAN` macro.
- All non-`_f` files were read; the large/branchy ones (`library_graph_map.c`,
  `library_graph_map_view.c`, `library_graph_map_io.c`, `library_graph_order.c`,
  `library_mesh_order.c`, `library_graph_color.c`, `library_context.c`,
  `library_arch*.c`, `library_graph.c`, `library_mesh.c`, `library_dmesh*.c`) were
  read in full. Fortran stubs were spot-checked (fd-duplication error paths in the
  two-stream geometry stubs are correct; `fdopen`/`fclose` balance checks out).
- Note: `library_dmesh*.c` (new, dated Aug 2025, PT-Scotch `SCOTCH_Dmesh` API) sits
  in this territory by filename and is covered briefly.

## Architecture

- **Opaque dummy-sizing.** Public structs (`SCOTCH_Graph`, `SCOTCH_Arch`, ...) are
  double-aligned byte blobs declared in `scotch.h`. Each `SCOTCH_*Init` verifies
  `sizeof (SCOTCH_X) >= sizeof (X)` and `sizeof (SCOTCH_Num) == sizeof (Gnum)` at run
  time and errors out otherwise. `SCOTCH_*Alloc`/`SCOTCH_*Sizeof` helpers exist for
  binding authors (this is what PyScotch must use instead of hardcoded sizes).
- **Rename machinery.** Every public symbol is spelled `SCOTCH_x` in source and is
  remapped by the `module.h` rename table when building suffixed variants
  (int32/int64 coexistence). Error messages are produced via
  `errorPrint (STRINGIFY (SCOTCH_x) ": ...")`, so a symbol missing from the rename
  table both breaks coexistence *and* is invisible until link/run time. (Known
  omissions — `SCOTCH_memFree`, `SCOTCH_contextAlloc`, `SCOTCH_meshBuildElem` —
  already reported; not re-audited here.)
- **Context containers.** `SCOTCH_contextBindGraph/Mesh/Dgraph` overwrite a
  `SCOTCH_Graph`-sized blob with a `ContextContainer { flagval = 0x4000, contptr,
  dataptr }`. The trick is that `flagval` overlays the contained object's `flagval`
  field (graph flags only use `0x003F`). API entry points must therefore unwrap via
  `CONTEXTOBJECT()` (data accessors) or `CONTEXTDECL/CONTEXTINIT/CONTEXTEXIT`
  (computation routines, which also create an ephemeral default context when the
  object is not bound). **The graph API does this consistently; the mesh API almost
  entirely does not** (see Finding 9).
- **Error conventions.** Nominal contract: 0 = success, 1 = "operation not
  possible", 2+ = error. In practice most wrappers only distinguish 0 / !0, and
  several documented 0/1/2 functions return 1 for hard errors (Finding 11).
  `errorPrint` itself comes from whichever error library is linked:
  `libscotcherr` (prints, returns) or `libscotcherrexit` (prints, `exit()`s). Some
  code assumes the exiting variant (Finding 1).
- **FILE\* usage.** All I/O routines take `FILE *` directly. Fortran stubs
  `dup()` the integer unit, `fdopen()` it, and `fclose()` after the call. C callers
  (and ctypes bindings) must pass real C streams of the same libc the library was
  linked against.

## Code-quality observations

- The layer is mostly thin and mechanical, but a handful of files contain real
  algorithmic code rather than delegation: `library_graph_color.c` (the whole
  greedy coloring lives in the wrapper), `library_graph_map_view.c` (~800 lines of
  statistics), `library_graph_map_io.c` (mapping file parsing),
  `library_graph_order.c` (partial-order list plumbing). Unsurprisingly, all
  findings below cluster in these files.
- Based-array (`-tax` = table minus base) vs un-based (`-tab`) pointer conversions
  are done by hand at every boundary; the majority of the bugs found are exactly
  missed or double base adjustments, invisible with `baseval == 0`.
- Doc-comment hygiene is weak: copy-pasted comments (e.g. `SCOTCH_graphColor` doc
  says "if the graph has been coarsened"), stale return-value contracts.
- Debug-only paths (`SCOTCH_DEBUG_LIBRARY*`, `SCOTCH_DEBUG_MAP2`) occasionally
  `return` without freeing group allocations (e.g. `library_graph_map_view.c:439`
  area); leaks only under debug builds, not listed as findings.

## Findings

### 1. `SCOTCH_graphPartOvlView`: missing `return` after failed allocation → UB
`library_graph_map_view.c:709-718` (high)

```c
  if (memAllocGroup ((void **) (void *)
                     &compload, (size_t) (partnbr * sizeof (Gnum)),
                     &compsize, (size_t) (partnbr * sizeof (Gnum)),
                     &listtab,  (size_t) ((partnbr + 1) * sizeof (GraphMapViewList)), NULL) == NULL) {
    errorPrint (STRINGIFY (SCOTCH_graphPartOvlView) ": out of memory");
  }
  listtab ++;                                     /* TRICK: Trim array so that listtab[-1] is valid */
  memSet (listtab, ~0, partnbr * sizeof (GraphMapViewList)); /* Set vertex indices to ~0            */
```

Every sibling in this layer does `errorPrint (...); return (1);` (or `goto abort`).
Here the error branch falls through. On allocation failure `memAllocGroup` sets
only its *first* output (`compload`) to NULL and leaves `compsize`/`listtab`
uninitialized (`common_memory.c:508-511`), so the following `listtab ++` /
`memSet` operate on an indeterminate pointer — undefined behavior with the default
non-exiting `libscotcherr`. The function's own header comment ("- exit : on error
(because of errorPrint)") shows it was written assuming the `errexit` variant.

### 2. `SCOTCH_graphRemapView`: migration distance computed between old domain and itself
`library_graph_map_view.c:485-489` (high)

```c
      if (parotax[vertnum] != parttax[vertnum]) {
        migrnbr ++;
        archDomTerm (archptr, &domnorg, parotax[vertnum]); /* Get terminal domains */
        archDomTerm (archptr, &domnold, parotax[vertnum]);
        migrdistavg += archDomDist (archptr, &domnorg, &domnold);
```

Both `archDomTerm` calls take `parotax[vertnum]` (the *old* part); one of them
should take `parttax[vertnum]`. `archDomDist (a, x, x) == 0` always, so the
reported `AvgMigrDist` is 0 whenever any migration occurred. Classic copy-paste
twin divergence. (Additionally, `parttax` at this point holds renumbered dense
indices, not terminal numbers — see Finding 4 — so even with the correct variable
the distance would use the wrong terminal number whenever renumbering is not the
identity.)

### 3. `SCOTCH_graphTabLoad`: vertex label array indexed un-based
`library_graph_map_io.c:150-155` (high for graphs with `baseval != 0`)

```c
    for (vertsortnum = 0; vertsortnum < vertnbr; vertsortnum ++) {
      vertsorttab[vertsortnum].labl = grafptr->vlbltax[vertsortnum];
      vertsorttab[vertsortnum].num  = vertsortnum;
```

`vlbltax` is a *based* pointer (`graph_io.c:178`: `vlbltax = vlbltab - baseval`),
yet it is indexed with the un-based counter `0..vertnbr-1`. For a base-1 labeled
graph this reads `vlbltab[-1]` (out-of-bounds) and associates every vertex with its
predecessor's label, so the loaded partition values land on the wrong vertices.
The twin `SCOTCH_graphTabSave` in the same file is correct
(`library_graph_map_io.c:215-217` iterates `vertnum` from `baseval` to `vertnnd`).
`SCOTCH_graphMapLoad` funnels into this routine, so mapping reload on based,
labeled graphs is broken.

### 4. `SCOTCH_graphMapView` family destructively rewrites the user's part array
`library_graph_map_view.c:315-320` (high confidence that the mutation occurs;
medium that it matters in common configurations)

```c
  for (vertidx = 0; domntab[vertidx].labl != ARCHDOMNOTTERM; vertidx ++) {
    parttax[domntab[vertidx].peri] = mapnbr;      /* Build map of partition parts starting from 0  */
```

`parttax` is `lmapptr->parttab` (the user's array, possibly the very `parttab` the
user passed to `SCOTCH_graphMapInit`), rebased at line 303. A "view" (read-only by
any reasonable expectation, and by its `const SCOTCH_Mapping *` parameter) replaces
the terminal domain numbers with dense 0-based ranks. When all terminals of the
architecture are used the renumbering is the identity and nobody notices; when
some terminals are unused (mapping onto a sub-architecture, variable-sized archs),
the user's mapping is silently corrupted, and the subsequent
`archDomTerm (archptr, ..., parttax[...])` calls inside the same function compute
communication statistics for the *wrong* terminal domains. Related: if any vertex
is unmapped (`parttab[v] == -1`), it sorts *first* and matches the end sentinel
`ARCHDOMNOTTERM` (== -1, `arch.h:101`), so the whole statistics loop exits at
`vertidx == 0` and most reported figures degenerate to 0 — the sentinel trick and
the "unmapped" encoding collide.

### 5. `SCOTCH_graphRemapView`: old part array never rebased
`library_graph_map_view.c:271` vs `:303` and `:483` (medium-high; base-1 only)

```c
    parotax = lmaoptr->parttab;                   /* line 271: no "- baseval"  */
  ...
  parttax -= grafptr->baseval;                    /* line 303: parttax only    */
  ...
      if ((parttax[vertnum] == -1) || (parotax[vertnum] == -1))  /* line 483   */
```

`parotax` is used with based indices `vertnum ∈ [baseval, vertnnd)` but is never
rebased. For base-1 graphs all old-part reads are shifted by one and the last read
is out of bounds. Same latent-for-base-0 class as Finding 3.

### 6. `graphMapView3` (part pseudo-diameter): loop bound mixes based index with count
`library_graph_map_view.c:127-134` (medium-high; base-1 only)

```c
  for (passnum = 1, rootnum = grafptr->baseval; ; passnum ++) {
    ...
    while ((rootnum < grafptr->vertnbr) &&
           ((vexxtax[rootnum].passnum != 0) ||    /* Find first unallocated vertex */
            (parttax[rootnum] != partval)))
      rootnum ++;
    if (rootnum >= grafptr->vertnbr)              /* Exit if all of graph processed */
```

`rootnum` is a based vertex index (starts at `baseval`) compared against the
un-based count `vertnbr`; the bound should be `vertnnd`. For base-1 graphs the last
vertex is never considered as a component root, so a connected component consisting
of (or reachable only from) that vertex is skipped in the `PartDiam` statistics.
Also, this helper returns -1 on allocation failure and the caller
(`library_graph_map_view.c:536-547`) adds it into `diamsum`/`diammin` unchecked.

### 7. `SCOTCH_graphDiamPV`: error return violates its own contract
`library_graph_diam.c:66-84` (high)

```c
*** It returns:
*** - [0; GNUMMAX[ : graph pseudo-diameter.
*** - GNUMMAX      : disconnected graph.
*** - < 0          : on error.
+*/
...
  if (CONTEXTINIT (libgrafptr) != 0) {
    errorPrint (STRINGIFY (SCOTCH_graphDiamPV) ": cannot initialize context");
    return     (1);
  }
```

The documented error channel is a negative value (and `graphDiamPV` itself does
return -1 on error), but the context-initialization failure path returns +1 — a
perfectly valid pseudo-diameter. Callers checking `< 0` cannot detect this error.

### 8. `SCOTCH_graphStat`: `edlosum` differs by a factor of 2 between branches
`library_graph.c:489-517` (medium)

```c
    if (srcgrafptr->edlotax != NULL) {            /* If graph has edge loads */
      ...
          edlosum += srcgrafptr->edlotax[edgenum]; /* summed over ALL arcs (each edge twice) */
      ...
    }
    else {
      ...
      edlosum = srcgrafptr->edgenbr / 2;          /* number of edges (arcs / 2) */
```

With edge loads, `edlosum` accumulates over every arc, counting each undirected
edge twice; without edge loads it reports `edgenbr / 2`, counting each edge once.
One of the two conventions is wrong (the manual, `doc/src/scotch/s_l.tex:3763`,
just says "the sum of all edge loads"). Also inconsistent with `SCOTCH_graphBuild`,
which sets the internal `edlosum = edgenbr` (arc count) in the unweighted case.

### 9. Mesh API ignores context containers; graph twins handle them
`library_mesh.c`, `library_mesh_graph.c`, `library_mesh_io_habo.c`,
`library_mesh_io_scot.c` (medium)

`SCOTCH_contextBindMesh` exists (`library_context_mesh.c`) and creates a mesh
container, but of the whole mesh API only `SCOTCH_meshOrderCompute*`
(`library_mesh_order.c`, via `CONTEXTINIT`) unwraps it. In particular:

```c
void
SCOTCH_meshExit (
SCOTCH_Mesh * const         meshptr)
{
  meshExit ((Mesh *) meshptr);                    /* library_mesh.c:132 */
}
```

versus the graph twin `library_graph.c:139` (`if (! contextContainerTrue (grafptr))
graphExit (...)`) and even the brand-new dmesh twin `library_dmesh.c:129` which has
the guard. `SCOTCH_meshLoad/Save/Check/Size/Data/Stat`, `SCOTCH_meshGraph[Dual]`
and the mesh geometry I/O all cast the pointer directly, so passing a bound mesh
container (legal for ordering) to any of them misinterprets the container as a
`Mesh`. `meshExit` on a container reads garbage pointer fields (crash potential);
the graph-side equivalents all unwrap. The newest file having the guard suggests
the mesh side is an unmaintained gap, not a design decision.

### 10. `SCOTCH_graphDump` does not unwrap context containers
`library_graph_dump.c:87` (medium-low)

```c
  grafptr = (const Graph *) libgrafptr;
```

Sole graph-API data routine that casts directly instead of using
`CONTEXTOBJECT()` (compare `SCOTCH_graphSave`, `library_graph.c:210`). Dumping a
context-bound graph reads the container as a `Graph`.

### 11. 0/1/2 return contract violated on error paths of coarsening/coloring wrappers
`library_graph_coarsen.c:98-100,136-139,170-172`, `library_graph_color.c:95-98,112`
(medium)

```c
*** - 0  : if the graph has been coarsened.
*** - 1  : if the graph could not be coarsened.
*** - 2  : on error.
+*/
...
  if (CONTEXTINIT (finegrafptr) != 0) {
    errorPrint (STRINGIFY (SCOTCH_graphCoarsen) ": cannot initialize context");
    return (1);
  }
```

`SCOTCH_graphCoarsen` / `SCOTCH_graphCoarsenMatch` document 1 = "could not
coarsen" (benign) and 2 = error, but return 1 for a hard context-allocation
failure; callers (including PyScotch, which per project knowledge treats 1 as
"cannot coarsen, coarse graph invalid but not an error") cannot distinguish the
two. `SCOTCH_graphColor` likewise documents 2 = error yet returns 1 on both
context failure and out-of-memory (`o = 1; /* Assume an error */`, line 112). Its
doc comment is a coarsen copy-paste besides.

### 12. `SCOTCH_archSub` alone returns 2 for the internal sizing error
`library_arch.c:448-451` (low)

```c
  if (sizeof (SCOTCH_Num) != sizeof (Gnum)) {
    errorPrint (STRINGIFY (SCOTCH_archSub) ": internal error");
    return (2);
  }
```

All ~12 sibling `SCOTCH_arch*` constructors in the same file return 1 from the
identical check. Harmless under the documented "!0 = error", but a copy-paste
divergence worth normalizing.

### 13. `SCOTCH_archBuild0`: default-strategy `stratInit` result never checked
`library_arch_build.c:132-136` (low)

```c
  if (*((Strat **) stratptr) == NULL)             /* Set default mapping strategy if necessary */
    *((Strat **) stratptr) = stratInit (&bgraphbipartststratab, "(m{vert=50,...})...");
  bipstratptr = *((Strat **) stratptr);
  if (bipstratptr->tablptr != &bgraphbipartststratab) {
```

If `stratInit` returns NULL (out of memory), `bipstratptr->tablptr` dereferences
NULL. Every other default-strategy site in the layer goes through
`SCOTCH_stratGraphXxxBuild`, which checks. Also, the error message at
`library_arch_build.c:95` stringifies the wrong name: `STRINGIFY (SCOTCH_stratBipart)`
inside `SCOTCH_stratGraphBipart` (and it bypasses the rename table, since
`SCOTCH_stratBipart` is not a declared symbol).

### 14. `SCOTCH_contextOptionParse` ignores failures of `SCOTCH_contextOptionSetNum`
`library_context.c:368` (low; interacts with the already-known switch-on-value bug)

```c
    SCOTCH_contextOptionSetNum (libcontptr, argsptr->vtypidx, argsptr->vtypval); /* Set options value */
```

Return value dropped; the parse routine then returns 0. Given the known bug that
`SCOTCH_contextOptionSetNum` switches on the *value* (so e.g. table entries with
value 0 are dispatched through the wrong case), parse strings like `"u"` or `"r"`
can silently misbehave with no error surfaced to the caller.

### 15. `errorProg`: shrinking the program name leaves stale suffix
`library_error.c:77-98` (also duplicated in `library_error_exit.c`) (low)

```c
  charnbr = strlen (progstr);
  ...
  strncpy (ndstptr, nsrcptr, charnbr);
  _SCOTCHerrorProgName[31] = '\0';
```

`strncpy` with `charnbr == strlen (progstr)` copies no terminator, and only index
31 is forced to NUL. A second call with a shorter name than the first leaves the
previous name's tail appended (e.g. `errorProg ("gmap")` after
`errorProg ("gpart_verbose")` yields `"gmap_verbose"`). Only affects programs that
call `SCOTCH_errorProg` more than once.

### 16. Init-return asymmetries in high-level convenience wrappers
`library_graph_order.c:413` vs `:447`; `library_mesh_order.c:319,351` (low)

`SCOTCH_graphOrder` checks `SCOTCH_graphOrderInit (...) != 0`, but its siblings
`SCOTCH_graphOrderList`, `SCOTCH_meshOrder`, `SCOTCH_meshOrderList` call the same
Init and ignore the result (`orderInit` allocates `peritab` when the user passed
none; on failure the subsequent Compute dereferences NULL). Same pattern in
`library_graph_map.c`: `SCOTCH_graphMap/Remap/...` never check
`SCOTCH_graphMapInit`, which can fail with out-of-memory when `parttab == NULL`.

### 17. `SCOTCH_graphTabLoad`: empty mapping rejected + dead code
`library_graph_map_io.c:98-107` (low)

```c
  if ((fscanf (stream, GNUMSTRING, &mappfileval) != 1) || /* Read number of mapping pairs */
      (mappfileval < 1)) {
    errorPrint (STRINGIFY (SCOTCH_graphTabLoad) ": bad input (1)");
    return     (1);
  }
  mappfilenbr = (Gnum) mappfileval;

  if (mappfilenbr <= 0)                           /* If nothing to do */
    return (0);
```

The `<= 0` early-success branch is unreachable because `< 1` was already rejected
as an error; a mapping file with zero pairs (which `SCOTCH_graphTabSave` can
produce for an empty graph) fails to load. The two checks encode contradictory
intents.

### 18. New `SCOTCH_dmesh*` API: sizing checks demoted to debug; Build accepts base -1
`library_dmesh.c:105-115`, `library_dmesh_build_adm.c:84-87` (low)

`SCOTCH_dmeshInit` wraps its `sizeof` consistency checks in
`#ifdef SCOTCH_DEBUG_DMESH2` whereas every other `SCOTCH_*Init` performs them
unconditionally; a 32/64 mismatch goes undetected in release builds.
`SCOTCH_dmeshBuildAdm` validates `(baseval < -1) || (baseval > 1)` — accepting -1,
which only makes sense for *Load*-style routines (copy-paste of
`library_mesh.c:152`), while its comment says "base to 0 or 1".

## Test coverage (src/check/)

Sequential-API check programs: `test_scotch_arch`, `test_scotch_arch_deco`,
`test_scotch_context`, `test_scotch_graph_coarsen`, `test_scotch_graph_color`,
`test_scotch_graph_diam`, `test_scotch_graph_dump`, `test_scotch_graph_induce`,
`test_scotch_graph_map(_copy)`, `test_scotch_graph_order`,
`test_scotch_graph_part_ovl`, `test_scotch_mesh_graph`, `test_strat_seq/par`,
`test_common_random`.

Wrappers with **no C test at all** (exercised, at best, only by the command-line
programs in `src/scotch/`, which are not part of `make check` assertions):

- `library_graph_map_view.c` — entire family (`SCOTCH_graphMapView`,
  `RemapView`, `*ViewRaw`, `graphPartOvlView`). Findings 1, 2, 4, 5, 6 live here.
- `library_graph_map_io.c` — `SCOTCH_graphTabLoad/TabSave/MapLoad/MapSave`
  (Finding 3). `test_scotch_graph_map` calls `SCOTCH_graphMapSave` only.
- Graph/mesh geometry I/O: all of `library_graph_io_{chac,habo,mmkt,scot}.c`,
  `library_mesh_io_{habo,scot}.c`.
- `library_mesh_order.c` — the whole mesh ordering API. Mesh API coverage overall
  is a single test (`test_scotch_mesh_graph`: `meshInit/meshLoad/meshGraph/meshExit`);
  `meshSave/meshCheck/meshData/meshStat/meshBuild` are untested.
- `SCOTCH_graphStat`, `SCOTCH_graphData`, `SCOTCH_graphBase` (Finding 8 would not
  be caught).
- Public random wrappers `SCOTCH_random{Load,Save,Proc,Reset,Seed,Val}`
  (`test_common_random` drives internal `intRand*` directly).
- `library_memory.c`, `library_common.c`, `library_version.c`, `library_geom.c`.
- The new `library_dmesh*.c` API.
- Context option routines `SCOTCH_contextOption{GetNum,SetNum,Parse}` — untested,
  which is how the known switch-on-value bug survived.

## PyScotch relevance (ctypes binding hazards)

- **Return-code deviations to special-case:** `SCOTCH_graphDiamPV` returns +1 on
  context failure despite the "< 0 on error" contract (Finding 7); coarsen/color
  return 1 for hard errors (Finding 11), so PyScotch's "1 = benign cannot-coarsen"
  rule misclassifies OOM/context failures. `SCOTCH_archSub` may return 2 where
  siblings return 1.
- **Views are not read-only:** `SCOTCH_graphMapView`/`RemapView` can rewrite the
  user-supplied `parttab` in place (Finding 4). If PyScotch exposes map-view
  helpers, copy the array first or document the mutation.
- **Ownership:** `SCOTCH_graphMapInit (..., parttab=NULL)` and
  `SCOTCH_graphMapLoad` allocate an internal part array freed by
  `SCOTCH_graphMapExit` (`LIBMAPPINGFREEPART`); a user-provided array is borrowed,
  never copied. `SCOTCH_graphBuild`/`SCOTCH_meshBuild` keep raw pointers into the
  caller's arrays for the life of the graph — the numpy buffers must outlive the
  `SCOTCH_Graph`. `SCOTCH_archSub` builds on top of the original arch; keep the
  parent alive. `SCOTCH_graphData` returns pointers into Scotch-owned (or
  user-owned) memory, valid only while the graph is.
- **Strategy lifetime:** `SCOTCH_stratExit` frees but does not NULL the handle
  (unlike `SCOTCH_stratFree`); calling it twice is a double free. Also,
  `SCOTCH_graphOrderCompute`-style routines silently *replace* a NULL strategy
  inside the caller's `SCOTCH_Strat` with a default one — the binding must still
  exit it.
- **Contexts and meshes don't mix** (Finding 9): only `SCOTCH_meshOrderCompute*`
  accepts a bound mesh; `SCOTCH_meshExit` on a container is memory-unsafe. On the
  graph side everything unwraps except `SCOTCH_graphDump`.
- **Base-1 graphs are a minefield in the stats/I-O layer** (Findings 3, 5, 6):
  if PyScotch ever surfaces `graphTabLoad`/`graphMapLoad` or the view routines,
  prefer rebasing graphs to 0 on the Python side first.
- **`SCOTCH_graphColor`** requires a non-NULL `coloptr` (written unconditionally)
  and a `colotab` of exactly `vertnbr` `SCOTCH_Num`s (pre-`memSet` by the routine);
  it is implemented wholly in the wrapper and needs the context's RNG —
  reset-before-call guidance in CLAUDE.md remains correct.
- **`SCOTCH_archLtleaf`** writes the inverse permutation with
  `peritab[permtab[i]] = i` without validating `permtab[i] < permnbr`
  (`library_arch.c:539-540`) — validate the permutation in Python before calling,
  or an out-of-bounds write occurs inside Scotch-owned memory.
