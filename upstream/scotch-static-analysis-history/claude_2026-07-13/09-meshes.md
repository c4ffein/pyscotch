# Meshes — Scotch v7.0.11

## Scope

Reviewed (all under `external/scotch/src/libscotch/`):

- **Core mesh** (8 files): `mesh.c`, `mesh_check.c`, `mesh_graph.c`, `mesh_coarsen.c`, `mesh_induce_sepa.c`, `mesh_io.c`, `mesh_io_habo.c`, `mesh_io_scot.c` (+ `mesh.h`, `mesh_graph.h`, `mesh_coarsen.h`)
- **Halo meshes / ordering** (15 files): `hmesh.c`, `hmesh_check.c`, `hmesh_hgraph.c`, `hmesh_induce.c`, `hmesh_mesh.c`, `hmesh_order_{bl,cp,gp,gr,hd,hf,hx,nd,si,st}.c` (+ `hmesh.h`)
- **Mesh separators** (9 files): `vmesh.c`, `vmesh_check.c`, `vmesh_store.c`, `vmesh_separate_{fm,gg,gr,ml,st,zr}.c` (+ `vmesh.h`)
- Supporting context: `library_mesh.c`, `library_mesh_order.c`, `graph_check.c`, `graph_base.c`, `common.h`, `src/check/Makefile`, `src/check/test_scotch_mesh_graph.c`.

The three algorithm-heavy groups (`mesh_coarsen`/`mesh_io*`, `vmesh_separate_*`, `hmesh_order_*`) were audited by three sub-reviews; every finding quoted below was re-verified against the source at the cited line before inclusion.

## Architecture

**Bipartite element/node model.** A `Mesh` (mesh.h:107-128) is a graph whose vertices are split into two contiguous index ranges: elements in `[velmbas, velmnnd)` and nodes in `[vnodbas, vnodnnd)`. Edges only connect elements to nodes (checked by `meshCheck`). Either range may come first, but they must be adjacent (`velmnnd == vnodbas || vnodnnd == velmbas`). All adjacency arrays are `tax` pointers (pre-offset by base). Loads are split: `velotax` (element loads, based at `velmbas`... in principle) and `vnlotax` (node loads, based at `vnodbas`), with sums `velosum`/`vnlosum`. `vnumtax` exists only for (non-halo) nodes, is based at `vnodbas`, and its *contents* are based at `baseval` of the ancestor mesh. `veisnbr` counts isolated (degree-0) elements — several algorithms rely on it.

**A critical layout subtlety** (root cause of two findings below): `meshLoad` allocates **one** load array for elements and nodes together and sets `velotax == vnlotax` (mesh_io.c:162-171), both based at `baseval`. `SCOTCH_meshBuild`, by contrast, accepts **two independent user arrays** and bases them separately (library_mesh.c:234-235: `velotab - velmbas`, `vnlotab - vnodbas`). Some consumers assume the `meshLoad` layout — they index `velotax` with node numbers.

**Mesh→graph conversions** (`mesh_graph.c`):
- `meshGraphNodal`: nodes become graph vertices; two nodes are adjacent iff they share an element. Built via a per-vertex hash table of size ≥ `2·degrmax²`, with edge-array growth by 25% reallocation.
- `meshGraphDual`: elements become graph vertices; elements e1, e2 are adjacent iff they share at least `min(noconbr, degr(e1)−1, degr(e2)−1)` nodes (the threshold is `veconbr = MIN(noconbr, degr(e1)−1)` then `MIN(veconbr, degr(e2)−1)`, mesh_graph.c:301,322). A count-down field `nghbnbr` in the hash entry implements the threshold.

**Halo meshes** (`Hmesh`, hmesh.h:84-94): a mesh plus halo bookkeeping for nested-dissection ordering. Only nodes can be halo; halo nodes occupy the highest node indices (`vnohnnd = vnodbas + vnohnbr` splits non-halo from halo). Element adjacency lists are sorted non-halo-first, with `vehdtax[e]` marking the end of the non-halo sub-list; `veihnbr` counts elements whose neighbors are all halo. `hmeshHgraph` converts to a halo graph (nodal-style), `hmeshMesh` strips the halo (turning halo nodes into empty elements if nodes come first), `hmeshInducePart` builds the sub-halo-mesh of one part, `meshInduceSepa` builds the separator sub-mesh (nodes first, elements last, with a hash-based dedup of elements that connect the same separator nodes).

**Ordering** (`hmesh_order_*`): `st` dispatches a strategy tree; `nd` is nested dissection (calls `hmeshMesh` → `vmeshSeparateSt` → `meshInduceSepa` + `hmeshInducePart`, multithreaded via context split); `hd`/`hf` are halo AMD / halo approximate-minimum-fill fed by the shared `hx` array-filling helper; `cp` is compression; `gp` Gibbs-Poole-Stockmeyer; `gr` orders through the halo graph; `si` is the identity ordering; `bl` post-splits large blocks.

**Separation** (`vmesh_separate_*`): a `Vmesh` is a mesh plus `parttax` (elements ∈ {0,1}; nodes ∈ {0,1,2}, 2 = separator), part loads `ncmpload[3]`, `ncmploaddlt`, sizes, and `frontab`. `zr` moves everything to part 0; `gg` is greedy graph growing; `fm` is Fiduccia-Mattheyses refinement with hash tables + gain table; `ml` multilevel via `meshCoarsen` (HEM-style element matching); `st` dispatches; `gr` separates through `meshGraphNodal` on the nodal graph.

Entry point: `SCOTCH_meshOrderComputeList` (library_mesh_order.c:233-242) wraps the user `Mesh` in a no-halo `Hmesh` by aliasing `vehdtax = m.vendtax` — user arrays flow directly into all of the above.

## Code-quality observations

- The subsystem is visibly less finished than the graph side: shipped `TODO`s in hot paths (`vmesh_separate_fm.c:154`, `:362`; `mesh_graph.c:270`; `mesh_induce_sepa.c:346`; `mesh_coarsen.c:431` "TODO REMOVE"), a leftover unconditional debug `fprintf`, and an `exit(1)` stub where a hash-resize should be.
- Copy-paste artifacts: `hmeshMesh` error messages say `"hmeshHgraph: out of memory"` (hmesh_mesh.c:114,126); `mesh_check.c`'s header says "handles the source mesh functions".
- `meshCheck` is markedly weaker than `graphCheck`: it never validates `edgenbr` at all, and never bounds `verttax`/`vendtax` entries against the edge array (see Finding 7), whereas `graphCheck` validates `velosum` including overflow. `hmeshCheck` (hmesh_check.c) checks `vehdtax` range and `veihnbr`/`vnhlsum` but never `enohnbr`, and never verifies that edges before `vehdtax[e]` actually point to non-halo nodes and edges after it to halo nodes — a structurally invalid halo mesh passes.
- Error-path hygiene is uneven: most paths free the group leader correctly, but there is one wrong-pointer `free` (Finding 5), one leak of a first group when a second allocation fails (mesh_induce_sepa.c:194-207), and an unchecked shrinking `memRealloc` (hmesh_induce.c:362).
- Hash sizing is `degrmax²`-shaped everywhere (`mesh_graph.c:112,257`, `hmesh_hgraph.c:125,151`, `hmesh_order_hx.c:111`): quadratic memory in the maximum degree, and with 32-bit `Gnum` the product `degrmax * degrmax * 2` can overflow for `degrmax ≳ 32768`, yielding a too-small table and an infinite probe loop. Realistic FEM degrees are far below that; noted as latent. `hmeshHgraph` additionally pre-allocates `(degrmax²/2 + 1) * vnodnbr` edge slots (hmesh_hgraph.c:151) — a large over-allocation rather than starting small and growing.
- `memAlloc(0)` is safe throughout (`common.h:177/181` allocates `size | 8`).

## Findings

### 1. `vmeshSeparateFmResize` is an `exit(1)` stub — kills the host process — HIGH
`vmesh_separate_fm.c:154-156`:
```c
/* TODO */
  fprintf (stderr, "hertnum no longer valid !\n");
  exit    (1);
```
The FM hash-resize routine unconditionally terminates the process. It is called from three sites (lines 439, 650, 754) whenever the element or node hash table fills (`helmnbr >= hashmax` etc.). `hashmax` is derived from `hashnbr = 2*((fronnbr + movenbr)*(1 + edgenbr/vertnbr))` capped at `vertnbr` (lines 358-361) then inflated 4× (line 362) — small initial frontier + large mesh can genuinely exhaust it as FM explores. When triggered, the whole caller process (e.g. the Python interpreter using libscotch) exits. The code after `exit` is also internally wrong (the `memSet` at line 161 clears `[hashold, 3·hashold)` of the element table although the new table has `8·hashold` slots), i.e. the resize was never finished. Confidence: high that the code is as described; medium that real workloads reach it (the 4× inflation and the `vertnbr` cap mask it; the routine has clearly never run to completion in production).

### 2. `meshSave` writes garbage / wild-reads for weighted meshes in the canonical layout — HIGH
`mesh_io.c:351-358` (elements-first branch):
```c
  if (meshptr->velmbas <= meshptr->vnodbas) {     /* If elements first */
    vertnndtab[0] = meshptr->velmnnd;
    velotabtab[0] = meshptr->velotax;
    edgeadjtab[0] = meshptr->vnodbas - meshptr->baseval;
    vertbastab[1] = meshptr->vnodbas;
    velotabtab[0] = meshptr->vnlotax;
    edgeadjtab[1] = meshptr->velmbas - meshptr->baseval;
  }
```
Line 356 should be `velotabtab[1] = meshptr->vnlotax;`. As written it clobbers the element-load pointer (elements get node loads) and leaves `velotabtab[1]` **uninitialized stack memory**, which the save loop dereferences at line 385 (`velotax[vertnum]`) when the mesh has loads (`propstr[2] != '0'`, line 335). Elements-first is the canonical layout produced by every builder in the library. Effect: saving any weighted mesh produces corrupt output or crashes. The nodes-first `else` branch (lines 359-366) is correct, confirming the intent. Confidence: high.

### 3. `velotax`/`vnlotax` conflation: node loads read from the element load array — HIGH (code), MEDIUM (impact)
Two consumers index `velotax` with **node** numbers, which is only valid for `meshLoad`-built meshes where `velotax == vnlotax` is one shared full-range array (mesh_io.c:170-171):

- `mesh_induce_sepa.c:180` gates the weighted path on `if (orgmeshptr->velotax != NULL)` and line 230 reads
  ```c
  indvnloval  = orgmeshptr->velotax[orgvnodnum];
  ```
  with `orgvnodnum` a node vertex (also stores the result in the *induced* mesh's `velotax` based at `vnodbas`, lines 185-186, and sums it into `vnlosum` at line 347 — the induced mesh's node loads live in its `velotax` field with `vnlotax == NULL`).
- `hmesh_order_hx.c:106,130,168` (helper for both `hd` and `hf` orderings):
  ```c
  const Gnum * restrict const velotax = meshptr->m.velotax;
  ...
  nvtax[vertnum]  = (velotax != NULL) ? velotax[vnodnum] : 1;
  ```
  again `vnodnum` is a node vertex.

For a mesh built with `SCOTCH_meshBuild` and *separate* load arrays (library_mesh.c:234-235) and then ordered (`SCOTCH_meshOrder` → `hmeshOrderNd`/`hd`/`hf` → these routines):
- `velotab != NULL`: `velotax[vnodnum]` reads element-array index `vnodnum - velmbas ∈ [velmnbr, velmnbr + vnodnbr)` — **out of bounds of the user's element load array** → garbage (possibly negative) node loads or a crash.
- only `vnlotab != NULL` (the meaningful case — node loads = DOFs): `velotax == NULL`, so node loads are **silently ignored** by the separator sub-mesh and by AMD/AMF weighting.

For internally induced meshes (`hmeshInducePart` allocates `velotax` sized `velmnbr` and `vnlotax` sized `vnodnbr` as adjacent group members, hmesh_induce.c:143-144), the OOB read lands in `vnlotax` by memory-layout accident and "works". Confidence: high that the code reads the wrong array; medium on real-world impact (weighted mesh ordering through the public API is clearly untested — see Test coverage).

### 4. `hmeshMesh`: operator-precedence bug in the nodes-first halo branch — HIGH (code), LOW (reachability)
`hmesh_mesh.c:130`:
```c
memCpy (meshptr->vendtax + hmshptr->vnohnbr, hmshptr->m.verttax + hmshptr->vnohnnd, hmshptr->m.vnodnbr - hmshptr->vnohnbr * sizeof (Gnum)); /* Create empty fake element part */
```
`hmshptr->vnodnbr - hmshptr->vnohnbr * sizeof (Gnum)` parses as `vnodnbr − (vnohnbr·8)`, not `(vnodnbr − vnohnbr)·8`. If `8·vnohnbr > vnodnbr` (almost always) the byte count is negative → converted to a huge `size_t` → `memCpy` crash; otherwise a short copy leaves `vendtax` entries uninitialized. Mitigating: this branch requires a halo mesh with nodes numbered before elements; `hmeshInducePart` always builds elements-first (hmesh_induce.c:132-134) and the top-level `Hmesh` has no halo (library_mesh_order.c:237-238 → the early return at hmesh_mesh.c:102-109), so the standard ordering pipeline cannot reach it. Latent bug, plus the wrong `"hmeshHgraph"` error strings at lines 114/126. Confidence: high (bug), low (reachability).

### 5. `hmeshOrderNd`: `free()` of an interior group pointer on an error path — HIGH (code), LOW (reachability)
`hmesh_order_nd.c:213-217`:
```c
    if (meshInduceSepa (&nspmeshdat.m, nspmeshdat.parttax, nspmeshdat.fronnbr, nspmeshdat.frontab, &indmeshdat.m) != 0) {
      errorPrint ("hmeshOrderNd: cannot build induced subgraph (1)");
      memFree    (nspmeshdat.frontab);            /* Free remaining space */
      return (1);
    }
```
`parttax` and `frontab` are one `memAllocGroup` block whose leader is `parttax` (lines 155-157); `vmeshExit` frees it via `parttax + baseval` (vmesh.c:77-78). `frontab` is an interior pointer, so this `memFree` is an invalid `free()` → heap corruption/abort; the path also leaks the mesh built by `hmeshMesh`. Every sibling error path correctly calls `vmeshExit(&nspmeshdat)` (lines 165, 171, 179). Only reachable when `meshInduceSepa` fails (OOM). Confidence: high.

### 6. `meshGraphDual` produces an inconsistent graph for element-weighted meshes — MEDIUM-HIGH
`mesh_graph.c:270-271`:
```c
  grafptr->velotax  = NULL;                       /* TODO: not implemented */
  grafptr->velosum  = meshptr->velosum;
```
With `velotax == NULL`, `graphCheck` requires `velosum == vertnbr` (graph_check.c:118,193). A mesh with element loads (`velosum ≠ velmnbr`) yields a dual graph that fails `graphCheck` and, worse, silently mis-weights anything that trusts `velosum` (bipartitioning balance) while per-vertex weights are treated as 1. Unweighted meshes are unaffected (`velosum == velmnbr`). `meshGraphNodal` handles the analogous case correctly (velotax/velosum from the node arrays, lines 126-130). Confidence: high for the inconsistency; medium for downstream impact.

### 7. `meshCheck` never validates `edgenbr` or edge-index bounds — can itself crash — MEDIUM-HIGH
`mesh_check.c:100-104` is the only validation of per-vertex indices:
```c
    if ((meshptr->verttax[vertnum] < meshptr->baseval) ||
        (meshptr->vendtax[vertnum] < meshptr->verttax[vertnum])) {
      errorPrint ("meshCheck: invalid vertex arrays (1)");
      return (1);
    }
```
There is no upper bound against the edge array (`meshptr->edgenbr` is never referenced anywhere in the function), so a mesh whose `verttax`/`vendtax` point past `edgetab` makes `meshCheck` itself read out of bounds at line 116 (`vertend = meshptr->edgetax[edgenum];`) — the validator crashes instead of reporting. It also cannot detect an `edgenbr` field inconsistent with the adjacency arrays, although `SCOTCH_meshBuild` stores the user-supplied `edgenbr` unvalidated. `degrmax` is only checked as an upper bound (`meshptr->degrmax < degrmax` fails, over-estimates pass — intended, several builders store estimates, e.g. mesh_induce_sepa.c:348). Confidence: high (verified against the whole function).

### 8. Leftover debug output in weighted coarsening — HIGH (certainty), LOW (severity)
`mesh_coarsen.c:431`:
```c
fprintf (stderr, "++ %ld %ld\n", (long) finevelmnum, (long) finemeshptr->velotax[finevelmnum]); /* TODO REMOVE */
```
Fires for every over-heavy element during weighted mesh coarsening (`meshCoarsenMatchNg`) — stderr pollution in a release build; confirms the weighted path is unexercised.

### 9. FM imbalance bound: computed value immediately overwritten — MEDIUM
`vmesh_separate_fm.c:333-345`: a block computes `ncmploaddltmat = max(deltrat·vnlosum + 1, edge-density term)`, then line 345 unconditionally re-assigns:
```c
  ncmploaddltmat = (paraptr->deltrat > 0.0L) ? ((Gnum) (paraptr->deltrat * meshptr->m.vnlosum) + 1) : 0;
```
making lines 333-343 dead code and the permitted imbalance tighter than the (commented) intent. Quality drift, not a crash. Confidence: high that the block is dead; medium on which version is intended.

### 10. Harwell-Boeing loader: unvalidated header/indices outside debug builds; `velosum` never set — MEDIUM
`mesh_io_habo.c`: header counts come from `atol` with no sign/overflow validation (lines 121-125) and flow into allocation sizes; the fixed-width field scanners never range-check parsed values in non-debug builds (the checks at lines 204-208, 236-240, 273-280 are `SCOTCH_DEBUG_MESH2`-only), so a corrupt file drives unchecked array-index writes, e.g. line 242 `meshptr->verttax[habnodval] ++;`. Separately, the loader sets `vnlosum = habvarnbr` (line 186) but never sets `velosum`, so a Habo-loaded mesh fails a subsequent `meshCheck` (`velosum` 0 ≠ `velmnbr`). Confidence: medium (paths verified; exploitability of the parser not exercised).

### 11. `hmeshOrderHd`/`Hf` ignore the error return of `hmeshOrderHxFill` — MEDIUM (OOM-only)
`hmesh_order_hd.c:139` and `hmesh_order_hf.c:143`:
```c
  hmeshOrderHxFill (meshptr, petab, lentab, iwtab, nvartab, elentab, &pfree);
```
`hmeshOrderHxFill` returns 1 on hash-table OOM (hmesh_order_hx.c:116-119) *before* filling the arrays or setting `pfree`; both callers proceed into the Fortran-style AMD/AMF kernels with uninitialized data (its header comment still says "returns void", so the error return was retrofitted without updating callers). Confidence: medium.

### 12. Smaller items — LOW
- `mesh.c:175-182` (`meshBase`): rebases `verttax/vendtax/edgetax/vnumtax/vlbltax` but **not** `velotax`/`vnlotax`, unlike `graphBase` (graph_base.c:117-124). No in-tree caller exists (only `hmeshBase`, itself uncalled), so purely latent — but `SCOTCH_meshLoad`'s `baseval` parameter is likewise never honored by rebasing.
- `mesh_induce_sepa.c:194-207`: if the first `memAllocGroup` succeeds and the second fails, the first is leaked (`return (1)` without freeing).
- `hmesh_induce.c:362`: shrinking `memRealloc` result unchecked; if `edgenbr == 0` (all-isolated selection) `realloc(p, 0)` may return NULL → later deref.
- `mesh_io.c:118-129`: `edgenbr` is the one header field with no `< 0` check (only saved from harm by allocation failure); no overflow check on `velmnbr + vnodnbr`.
- `mesh_io_scot.c:188-189`: `%d` format for a `Gnum` label (varargs UB on 64-bit `Gnum`, error path only).
- `hmesh_order_gp.c:187-191`: debug-only error return leaks `queue.qtab` (the later twin check at 233-237 frees it).
- `vmesh_separate_fm.c:362`: `/* TODO */ hashmax *= 4;` — a 4× (net 16× with `hashsiz = 4*hashmax`) working-memory inflation that also masks Finding 1.

Verified-clean areas worth recording: `meshCoarsen` handles zero-element meshes (empty loops, well-formed empty coarse mesh); `vmeshSeparateGg` handles the degenerate no-frontier case via `vmeshZero`; FM gain bookkeeping and write-back accounting are internally consistent; `vmesh_store.c`, `vmesh_check.c`, `hmesh_order_{si,bl,st,gr,cp}` and `hmeshInducePart`'s intricate two-way edge placement check out (its debug invariants are coherent). `hgraphInit` is called before `hmeshHgraph` by its one caller, so the conditionally-assigned `s.vnumtax`/`s.velotax` fields are safe in-tree.

## Test coverage

The mesh subsystem is close to untested upstream:

- **Unit tests**: exactly one, `src/check/test_scotch_mesh_graph.c` (117 lines): `meshInit` → `meshLoad(data/ship001.msh)` → `meshGraph` → exit. Return codes only — no `meshCheck` of the loaded mesh, no `graphCheck` (or any inspection) of the produced graph, unweighted input only.
- **Program-level checks** (`src/check/Makefile:638-659`): `mmk_m2`/`mmk_m3` generate small regular grid meshes; `mtst` prints stats; `mcv` round-trips source format (output diffed — the only output-validated mesh test); `mord` orders the grid meshes + `ship001.msh` and `gotst` validates the ordering. This does exercise `meshLoad`, `hmeshOrderNd/St`, `vmeshSeparate{St,Ml,Fm,Gg}`, `meshInduceSepa`, `hmeshInducePart`, `hmeshMesh`, `meshCoarsen` end-to-end — but only on small, **unweighted**, elements-first meshes.
- **Never exercised anywhere in the check suite**: `SCOTCH_meshCheck`, `SCOTCH_meshBuild`, `SCOTCH_meshSave` (Finding 2 would fail instantly on any weighted mesh), `SCOTCH_meshGraphDual`, `meshGraphNodal` on weighted meshes, any load-carrying path (Findings 2, 3, 6, 8 all live there), the Harwell-Boeing loader (Finding 10), nodes-first layouts (Finding 4), `meshBase`, `hmeshOrderCp/Gp/Hd/Hf` (not in the default strategy for these small cases — `hd` is in the default quality strategy but only reached above size thresholds), and the FM hash-resize path (Finding 1).
- Per CLAUDE.md's warning, "C test passes" means very little here even where coverage nominally exists — nothing validates outputs except `mcv`'s diff and `gotst`.

## PyScotch relevance

PyScotch (`pyscotch/mesh.py`) wraps `SCOTCH_meshInit/Exit/Load/Save/Build/Check/Graph/GraphDual/Order/Size` — precisely the least-tested upstream surface. Practical consequences:

1. **`save()` on a weighted mesh is broken upstream** (Finding 2): wild read or corrupt file. If PyScotch tests round-trip weighted meshes through save/load, they will hit this; until fixed upstream, only save unweighted meshes or meshes whose loads you can drop.
2. **`order()` on a `meshBuild`-built mesh with load arrays is unsafe** (Finding 3): separate `velotab` → OOB reads inside `meshInduceSepa`/`hmeshOrderHxFill`; only `vnlotab` → node loads silently ignored. Workaround if weighted ordering is ever needed: allocate **one** contiguous buffer of `velmnbr + vnodnbr` loads (elements first) and pass `velotab = buf`, `vnlotab = buf + velmnbr` — this reproduces the `meshLoad` shared-array layout the code actually assumes. Better: don't pass loads to meshes destined for ordering.
3. **A hard `exit(1)` is reachable from `order()`** (Finding 1): if FM refinement ever needs to grow its hash tables, the *Python process dies* with `hertnum no longer valid !` on stderr — not an exception, not a return code. Worth a note in QUESTIONS_FOR_SCOTCH_TEAM and a stress test on a large irregular mesh to establish whether default strategies can trigger it.
4. **`check()` is not a safety net** (Finding 7): `SCOTCH_meshCheck` never validates `edgenbr` and can itself segfault if `verttab`/`vendtab` entries exceed the edge array. PyScotch's ctypes layer should bounds-check `verttab`/`vendtab`/`edgetab` consistency in Python before calling into C on untrusted input, rather than relying on `meshCheck`.
5. **Dual graph semantics** (already understood in this repo, restated for completeness): `meshGraphDual(ncomm)` connects elements sharing ≥ `min(ncomm, degr(e1)−1, degr(e2)−1)` nodes — so degree-1 and degree-2 elements get edges more easily than `ncomm` suggests (threshold can drop to 0-but-they-share-one-node). Additional semantics binding authors should know: the dual graph of an **element-weighted** mesh carries `velosum = Σ element loads` with `velotax = NULL` (Finding 6) — an internally inconsistent Graph that `SCOTCH_graphCheck` rejects; and both conversions allocate hash tables of ~`2·degrmax²` entries, so one giant element (e.g. a lumped boundary element touching 10⁴ nodes) costs ~2·10⁸ hash slots.
6. `SCOTCH_meshBuild` computes `veisnbr`/`degrmax` itself (library_mesh.c:263-283) — bindings need not (and cannot) supply them; but it stores the caller's `edgenbr` unchecked (see 4).
7. `SCOTCH_meshBuildElem` / the broken 7.0.12 rename entry: known, already reported — not re-reported here.

For hand-verified small duals in `tests/`, the `min(ncomm, degr−1)` behavior above is the only intended subtlety; everything else surprising in this subsystem is, on the evidence, a bug rather than a semantic.
