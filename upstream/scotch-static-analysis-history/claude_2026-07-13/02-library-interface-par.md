# Library interface (parallel) — Scotch v7.0.11

## Scope

The 52 files `src/libscotch/library_dgraph*.c`, `library_dorder*.c`, `library_dmapping.c`:
the `SCOTCH_dgraph*` / `SCOTCH_dorder*` / `SCOTCH_dmap*` public C wrappers and their
Fortran shims (`*_f.c`) over the MPI-distributed implementations (`dgraph*.c`,
`dorder*.c`, `dmapping*.c` — read only where needed to confirm contracts). All C
wrappers were read in full; Fortran shims were read in full or scanned for the known
drift patterns.

## Architecture

### MPI_Comm handling
- `SCOTCH_dgraphInit` (library_dgraph.c:109) stores the user communicator by value in
  the `Dgraph`; **it is never duplicated** (`dgraph.c:99`). All later wrappers reuse
  `grafptr->proccomm` for their collectives. The communicator must stay valid for the
  graph's whole lifetime, and any MPI call by the caller on the same communicator that
  races with a Scotch collective can interleave.
- Fortran shims convert with `MPI_Comm_f2c`/`MPI_Comm_c2f` (library_dgraph_f.c) and
  `MPI_Type_f2c` for halo datatypes (library_dgraph_halo_f.c).
- Cross-graph communicator congruence (org vs band/coarse/induced/redistributed graph)
  is checked only under `SCOTCH_DEBUG_LIBRARY1` (`MPI_Comm_compare` in band.c:129,
  coarsen.c:126, induce.c:144, redist.c:91). Release builds silently assume congruence.

### Collective-call contracts
Collective (all ranks of the graph's communicator must call, with compatible
arguments): `dgraphLoad`, `dgraphSave`, `dgraphBuildGrid3D`, `dgraphCheck`,
`dgraphGhst`/`GhstReplace`, `dgraphHalo`/`HaloAsync`/`HaloWait`, `dgraphGather`,
`dgraphScatter`, `dgraphRedist`, `dgraphInducePart`, `dgraphBand`, `dgraphGrow`,
`dgraphCoarsen`, `dgraphStat`, `dgraphMapCompute`/`dgraphMap`/`dgraphPart`,
`dgraphMapStat`, `dgraphMapView`, `dgraphMapSave`, `dgraphOrderCompute`/`ComputeList`,
`dgraphOrderGather`, `dgraphOrderPerm`, `dgraphOrderCblkDist`, `dgraphOrderTreeDist`,
`dgraphOrderSave`/`SaveMap`/`SaveTree`/`SaveBlock`.
Local-only: `Init`/`Exit`/`Free`/`Alloc`/`Sizeof`/`Size`/`Data`, `dgraphMapInit`/
`MapExit`, `dgraphOrderInit`/`OrderExit` (dorderInit just records comm/rank),
`dgraphCorderInit`/`CorderExit`, strategy parsing/building.

When ranks disagree, there are two regimes:

1. **Symmetrized paths** — some routines deliberately fold local failure into a
   collective so all ranks agree: `dgraphBand` propagates local OOM through the
   `dgraphBand2*` call and an `MPI_Allgather` of `-1` (band.c:200-218);
   `dgraphMapStat` Allreduces an alloc-failure flag *and* the per-rank
   "which outputs are wanted" flags with `MPI_MAX` (map_stat.c:199), so a rank passing
   only NULL output pointers still executes the same collective blocks as the others;
   `dgraphGather`, `dmapSave`, `dorderSave`, `dorderSaveTree` elect the root by
   reduction and error out **on all ranks** if the root count is wrong.
2. **Asymmetric early returns** — most wrappers return before their first collective
   on context-init failure, strategy-table mismatch, `dgraphGhst` failure or OOM
   (e.g. order.c:190-232 before the `MPI_Allreduce` at :246; map_stat.c:184-187 before
   :199; stat.c:245 is executed only on ranks whose `edloloctax != NULL`). A rank that
   fails alone leaves the others blocked in the collective: deadlock, not error.

### Root-rank semantics (Save/View/Gather/Scatter)
- `SCOTCH_dgraphGather` (gather.c:77): the root is the rank passing a non-NULL
  `cgrfptr` (pointer equal to the dgraph also counts as NULL — Fortran sentinel).
  Contract enforced by Allreduce: **exactly one** root (gather to it) or **all ranks**
  roots (allgather); any other count → error on every rank (no deadlock).
- `SCOTCH_dgraphScatter` (scatter.c:77): the rank with non-NULL `cgrfptr` is the
  source; NULL / same-as-dgraph elsewhere.
- `SCOTCH_dgraphOrderSave`/`SaveMap`/`SaveTree`/`SaveBlock` and `SCOTCH_dgraphMapSave`:
  underlying `dorderSave`/`dorderSaveTree`/`dmapSave` elect the root as the rank whose
  `stream != NULL` and require exactly one (dmapping_io.c:101-118, dorder_io.c:90-104);
  0 or ≥2 non-NULL streams → symmetric error.
- `SCOTCH_dgraphSave` (io_save.c): the opposite — the distributed format writes one
  fragment per process, so **every** rank needs a valid stream (dgraph_io_save.c:72ff
  has no NULL-stream path).
- `SCOTCH_dgraphMapView` (map_view.c:83): stats computed collectively via
  `dgraphMapStat`; every rank whose `stream != NULL` prints the (identical, global)
  results. Conventional use: real stream on rank 0, NULL elsewhere.

### Dmapping / Dordering lifecycles
- `SCOTCH_Dmapping`: `dgraphMapInit` (map.c:83) wraps `dmapInit` and stashes the
  user's `termloctab` pointer inside the `LibDmapping` (NULL / graph-pointer sentinel
  = "no output"). `dgraphMapCompute` fills the internal fragment mapping and, only if
  `termloctab != NULL`, runs `dmapTerm` to export it. `dgraphMapExit` calls `dmapExit`
  unconditionally. The `SCOTCH_Arch` is captured by `dmapInit` and must outlive the
  mapping. `SCOTCH_dgraphMap`/`Part` are pure Init→Compute→Exit compositions.
- `SCOTCH_Dordering`: `dgraphOrderInit` calls `dorderInit` with the graph's baseval,
  global vertex count and communicator (so the graph must already be built).
  `OrderCompute[List]` begins with `dorderFree` (safe recompute), builds the column
  block tree collectively, and on the "list" variant splits the root block into
  ordered/unordered halves. Accessors (`OrderPerm`, `CblkDist`, `TreeDist`,
  `OrderSave*`) and `OrderGather` (into a `CorderInit`-prepared centralized
  `SCOTCH_Ordering`) follow; `OrderExit`/`CorderExit` free.

## Code-quality observations

- The Fortran shims are heavily copy-pasted and have drifted (findings F5-F9 below):
  by-value vs by-reference scalars, presence/absence of the `fileptr == -1` "no
  stream" sentinel, presence/absence of `revaptr`, symbol-name casing.
- `errorPrint` labels are occasionally wrong from copy-paste (order.c:96 says
  `SCOTCH_graphDorderInit`; grow.c:117 says `SCOTCH_dgraphBand`).
- Strategy builders (`stratDgraphMapBuild`, `ClusterBuild`, `OrderBuild`) build
  templates in `char bufftab[8192]` with `strcpy`/`stringSubst` and a "Should be
  enough" comment — currently true (~1.6 KB max) but unchecked.
- Doc-comment drift: `SCOTCH_dgraphStat` header says "returns VOID" but returns int
  (stat.c:111-117).
- `SCOTCH_dgraphHaloAsync` always returns 0 (the underlying `dgraphHaloAsync` is
  `void`, dgraph_halo.h:73); errors only surface at `HaloWait`. Harmless but the
  return value is a decoy.
- Statistics wrappers divide without zero guards: stat.c:316/325/336 divide by
  `vertglbnbr`/`edgeglbnbr`; map_view.c:135 divides by `edgeglbnbr / 2`;
  map_view.c:150-153 divides histogram cells by `cmlosum`. Empty/edgeless graphs
  print NaN/inf rather than erroring (MapStat itself early-outs cleanly at :134-164,
  so only View's own arithmetic is exposed when stats are all zero).
- `SCOTCH_dgraphMapStat` returns `ngbmin = ANUMMAX` if every target domain is empty
  (map_stat.c:403 never updated) — cosmetic, reachable only with fully unmapped input.

## Findings

**F1 (high) — NULL-pointer write on the OOM error path of `SCOTCH_dgraphBand`.**
library_dgraph_band.c:200-206:
```c
  if (cheklocval != 0) {                          /* In case of memory error */
    bandgrafptr->procdsptab[0] = -1;
    if (MPI_Allgather (&bandgrafptr->procdsptab[0], 1, GNUM_MPI, /* Send received data to dummy array */
```
If the **first** `memAllocGroup` (line 170, the one that allocates `procdsptab`
itself) fails, `memAllocGroup` sets its first pointer to NULL on failure
(common_memory.c:508-509), so `bandgrafptr->procdsptab` is NULL and line 201 writes
through it → segfault, defeating the very error-propagation collective it feeds. The
path is correct for failures of the second/third allocation groups (procdsptab then
valid). Mechanism: OOM on any rank → crash instead of the intended symmetric error.

**F2 (high, debug builds) — `SCOTCH_dgraphBand` returns success on failure under
`SCOTCH_DEBUG_LIBRARY1`.** library_dgraph_band.c:120-134:
```c
  o = 1;                                          /* Assume an error */
  ...
#ifdef SCOTCH_DEBUG_LIBRARY1
  MPI_Comm_compare (grafptr->proccomm, bandgrafptr->proccomm, &o);
  if ((o != MPI_IDENT) && (o != MPI_CONGRUENT)) {
```
`MPI_Comm_compare` overwrites the `o = 1` error sentinel. `MPI_IDENT` is 0 in MPICH
and Open MPI, so when the communicators are identical every subsequent `goto abort`
(dgraphGhst failure :136, OOM path :209, halo-sync failure :249, dgraphBuild4 failure
:351) returns `o == 0` = success with a garbage band graph. The sibling debug checks
in coarsen.c/induce.c/redist.c also clobber a temp but return explicit constants, so
only band is affected.

**F3 (medium) — `SCOTCH_dgraphMapView` CommDelta formula diverges from the sequential
twin.** library_dgraph_map_view.c:145-148:
```c
  fprintf (stream, "M\tCommDelta=%f\n",
           (((double) cmlosum  * (double) cmdisum) == 0.0L)
           ? (double) 0.0L
           : ((double) grafptr->edgeglbnbr) / (double) (cmlosum * 2));
```
library_graph_map_view.c:512-516 computes
`(commexpan * edgenbr) / (commload * commdilat)`. The parallel version's guard tests
`cmlosum * cmdisum` but the formula uses neither `cmexsum` nor `cmdisum` — it prints
`edgeglbnbr / (2*cmlosum)` (inverse average edge load), a different statistic.
Output-only, but PT-Scotch and Scotch report different "CommDelta" for the same
partition.

**F4 (low-medium) — missing NULL guard in `SCOTCH_dgraphCoarsen` user-array branch.**
library_dgraph_coarsen.c:148-165. The `multloctab == NULL` branch guards
`if (multlocptr != NULL)` before freeing; the user-provided-array + folding branch
does not:
```c
    if (foldval != DGRAPHCOARSENNONE) {           /* If folding took place, user array was not used */
      ...
      memCpy  (multloctab, multlocptr, coargrafptr->vertlocnbr * sizeof (DgraphCoarsenMulti));
      memFree (multlocptr);
```
When `dgraphCoarsen` returns 1 ("cannot coarsen") or 2, `multlocptr` can still be
NULL: `memCpy` from NULL and `memFree(NULL)`. Benign only as long as the failed
coarse graph's `vertlocnbr` is 0; per the known invariant "coarse graph is in an
invalid state when coarsening fails", that is not guaranteed on the error (2) path.

**F5 (high) — `SCOTCH_dgraphGrow` leaks the context and mislabels its error.**
library_dgraph_grow.c:116-127:
```c
  if (CONTEXTINIT (orggrafptr)) {
    errorPrint (STRINGIFY (SCOTCH_dgraphBand) ": cannot initialize context");
    ...
  if (dgraphGhst (&grafdat) != 0) {               /* Compute ghost edge array if not already present */
    errorPrint (STRINGIFY (SCOTCH_dgraphGrow) ": cannot compute ghost edge array");
    return (1);
  }
```
The `return (1)` bypasses `CONTEXTEXIT` (every other error path in the file goes
through `abort:`), leaking the context/thread resources acquired by `CONTEXTINIT`;
line 117's message names `SCOTCH_dgraphBand`. Copy-paste divergence from
`SCOTCH_dgraphBand`, which it was cloned from.

**F6 (high) — Fortran shim `SCOTCHFDGRAPHBAND` takes scalars by value.**
library_dgraph_band_f.c:79-84:
```c
SCOTCH_FORTRAN (                        \
DGRAPHBAND, dgraphband, (               \
SCOTCH_Dgraph * const       srcgrafptr, \
const SCOTCH_Num            fronlocnbr, \
SCOTCH_Num * const          fronloctab, \
const SCOTCH_Num            distval,    \
```
Every other shim declares scalars `const SCOTCH_Num * const` and dereferences
(cf. coarsen_f.c, induce_f.c, redist_f.c). Fortran passes by reference, so the shim
reinterprets the *addresses* of `fronlocnbr`/`distval` as their values — garbage
frontier size and distance, near-certain crash. The shim is unusable from Fortran.

**F7 (medium-high) — Fortran symbol for `dgraphStat` generated with wrong case.**
library_dgraph_stat_f.c:70: `SCOTCH_FORTRAN (DGRAPHSTAT, Dgraphstat, (...)`. The
second macro argument is the lowercase symbol stem; `FORTRAN2` (common.h:517-526)
emits `scotchfDgraphstat`, `scotchfDgraphstat_`, `scotchfDgraphstat__`. Compilers that
lowercase Fortran externals (gfortran default: `scotchfdgraphstat_`) will fail to
link `SCOTCHFDGRAPHSTAT`. Only the all-uppercase variant is emitted correctly.

**F8 (medium) — Fortran "no stream" sentinel missing from SaveMap/SaveTree/MapSave
shims.** `DGRAPHORDERSAVE` (library_dgraph_order_f.c:111-112) and `DGRAPHMAPVIEW`
(library_dgraph_map_view_f.c:82-83) accept `*fileptr == -1` → NULL stream, matching
the single-root contract of the underlying routines. `DGRAPHORDERSAVEMAP` and
`DGRAPHORDERSAVETREE` (library_dgraph_order_io_f.c:78, :114) and `DGRAPHMAPSAVE`
(library_dgraph_map_f.c:111) unconditionally `dup(*fileptr)`. Since `dorderSaveTree`
and `dmapSave` require **exactly one** rank with a non-NULL stream (dmapping_io.c:115
"should have only one root"), Fortran callers of these three routines cannot satisfy
the contract on >1 process: every rank must supply a valid fd, all become root
candidates, and the call fails on all ranks. Copy-paste divergence between the
Save/SaveMap/SaveTree family.

**F9 (low-medium) — `DGRAPHMAPSTAT` Fortran shim discards the error code.**
library_dgraph_map_stat_f.c: the shim calls `SCOTCH_dgraphMapStat(...)` (which returns
int and can fail: variable-sized archs, OOM, comm errors) with no `revaptr`, unlike
its sibling `DGRAPHSTAT`. Fortran callers cannot detect failure and read
uninitialized output arguments.

**F10 (medium) — Fortran output-sentinel recognition diverges between MapInit and
CorderInit/Redist under contexts.** `SCOTCH_dgraphMapInit` treats `termloctab` as
"unwanted" if it equals **either** the container pointer or the contextualized object
(library_dgraph_map.c:97-99). `SCOTCH_dgraphCorderInit`
(library_dgraph_order_gather.c:102-106) and `SCOTCH_dgraphRedist`
(library_dgraph_redist.c:101-102) compare only against `CONTEXTOBJECT(grafptr)`:
```c
  libcordptr->permtab = ((permtab == NULL) || ((void *) permtab == (void *) srcgrafptr)) ? NULL : (Gnum *) permtab;
```
For a graph bound into a `SCOTCH_Context` (container ≠ object), a Fortran caller
passing the graph itself as the sentinel gets that pointer accepted as a real output
array → `orderInit` builds `peritab` over the container / `dgraphRedist` reads it as
a partition array → memory corruption. Low likelihood (contexts + Fortran + sentinel
combined) but a clear Init-twin divergence. (`SCOTCH_dgraphScatter` has the mirror
gap: it checks `cgrfptr == dgrfptr` but not `cgrfptr == CONTEXTOBJECT(dgrfptr)`,
whereas `SCOTCH_dgraphGather` checks both.)

**F11 (medium) — per-rank `edloloctax` gates a collective in `SCOTCH_dgraphStat`.**
library_dgraph_stat.c:219-248: the `MPI_Allreduce` of the local edge-load sum is
executed only when `edgeglbnbr > 0 && edloloctax != NULL`. `edloloctax` is a
per-rank property: a rank with zero local edges that legitimately passed NULL
`edloloctab` to `dgraphBuild` skips the Allreduce and proceeds to the struct-typed
Allreduce at :295 while the other ranks sit in the first one — mismatched collectives
(deadlock or corrupted reduction). The library otherwise tolerates such graphs.

**F12 (low) — `SCOTCH_dgraphMap` ignores `SCOTCH_dgraphMapInit`'s return.**
library_dgraph_map.c:225-227. Init only fails on the `sizeof (SCOTCH_Dmapping) <
sizeof (LibDmapping)` guard, i.e. a broken build; but when it does, MapCompute and
MapExit then run on an uninitialized mapping. Cheap to check.

**F13 (low) — wrong routine name in `SCOTCH_dgraphOrderInit` error message.**
library_dgraph_order.c:96: `errorPrint (STRINGIFY (SCOTCH_graphDorderInit) ...)` —
no such routine; should be `SCOTCH_dgraphOrderInit`.

Not re-reported (already known): module.h rename omissions, `contextOptionSetNum`
index/value confusion, the 8 undocumented public functions.

## Test coverage (src/check/test_scotch_dgraph_*.c)

Seven MPI test programs exist: `band`, `check`, `coarsen`, `grow`, `induce`, `order`,
`redist`. Between them (plus `test_strat_par.c`) they exercise: `dgraphInit/Exit`,
`dgraphLoad`, `dgraphData`, `dgraphGhst`, `dgraphCheck`, `dgraphBand`,
`dgraphCoarsen(+VertLocMax)`, `dgraphGrow`, `dgraphInducePart`, `dgraphRedist`,
`dgraphOrderInit/Compute/ComputeList/Exit`, `dgraphCorderInit/Exit`,
`dgraphOrderGather`, `stratDgraphOrderBuild`, `stratDgraphMapBuild` (string-build
only, never executed on a graph).

**No test at all** for: `SCOTCH_dgraphMap`, `dgraphPart`, `dgraphMapInit/Compute/
Exit/Save`, `dgraphMapStat`, `dgraphMapView`, `stratDgraphMap`,
`stratDgraphClusterBuild` (the whole parallel mapping pipeline — the largest and
most-used part of this API — has zero check coverage); `dgraphGather`,
`dgraphScatter`, `dgraphSave`, `dgraphBuild`, `dgraphBuildGrid3D`, `dgraphStat`,
`dgraphHalo/HaloAsync/HaloWait/HaloReqAlloc/HaloReqSizeof`, `dgraphGhstReplace`,
`dgraphOrderPerm`, `dgraphOrderCblkDist`, `dgraphOrderTreeDist`,
`dgraphOrderSave/SaveMap/SaveTree/SaveBlock`, `dgraphFree`, `dgraphSize`,
`dgraphAlloc/Sizeof`, `dorderAlloc/Sizeof`, `dmapAlloc/Sizeof`. None of the Fortran
shims are compiled against by any test — which is how F6/F7/F8/F9 survive.

## PyScotch relevance

The new ctypes wrappers (dgraphPart/Map/Order/Gather/Scatter) sit exactly on this
layer. Concrete hazards:

- **NULL-vs-root conventions.** `dgraphGather`: pass an initialized `SCOTCH_Graph` on
  exactly one rank (or on all ranks for allgather) and NULL elsewhere; any other root
  count is a symmetric error, not a deadlock. `dgraphScatter`: source graph on one
  rank, NULL elsewhere. Do not "helpfully" pass the same non-NULL object everywhere
  on Gather unless allgather is intended.
- **`termloctab=None` is silently legal.** For `dgraphMap`/`dgraphPart`, NULL (or the
  graph pointer) is the Fortran "don't want output" sentinel (map.c:97-99): the call
  succeeds and the partition is discarded. A ctypes layer that maps `None` → NULL
  will return success with no data; require a real `vertlocnbr`-sized buffer.
- **Collective deadlock on one-rank errors.** Nearly every wrapper error-returns
  before its first collective (context init, strategy-table mismatch, `dgraphGhst`
  failure, OOM). If the Python layer raises on one rank (bad argument, allocation)
  after some ranks have already entered the C call, the others hang. Validate
  arguments symmetrically on all ranks *before* calling, and never call these
  functions from a subset of the communicator.
- **Strategies are per-rank objects.** The wrappers only check the strategy's method
  table, not that the text is identical across ranks. Different strategy strings on
  different ranks pass local validation and then diverge inside collective phases.
  Broadcast the strategy string (or build it deterministically) before use.
- **Stream arguments are rank-dependent.** `dgraphSave`/`dgraphLoad`: valid `FILE*`
  on **every** rank (one fragment per process). `dgraphOrderSave/SaveMap/SaveTree/
  SaveBlock`, `dgraphMapSave`: non-NULL on **exactly one** rank, NULL elsewhere.
  `dgraphMapView`: NULL suppresses printing per rank; stats are computed collectively
  regardless, so all ranks must call. Getting this wrong is at best "only one root"
  errors, at worst (dgraphSave with a NULL) a crash.
- **Edge/vertex load arrays must be globally consistent.** Passing edge loads on some
  ranks and None on others (e.g. a rank with zero local edges) trips F11-style
  mismatched collectives in `dgraphStat` and undefined behaviour elsewhere.
- **`dgraphBand`/`dgraphGrow` specifics** (if wrapped later): F1/F2/F5 mean OOM and
  debug-build error paths misbehave; also `fronloctab` for Band is in/out and must
  hold room for the result.
- **Communicator lifetime.** The `MPI_Comm` given to `SCOTCH_dgraphInit` is stored,
  not duplicated: keep the mpi4py communicator object alive as long as the Dgraph,
  and don't free it before `dgraphExit`.
