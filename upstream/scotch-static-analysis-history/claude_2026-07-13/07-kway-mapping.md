# K-way & mapping — Scotch v7.0.11

## Scope

Reviewed (submodule at `external/scotch`, tag v7.0.11, all paths below relative to `src/libscotch/`):

- `kgraph.c/.h`, `kgraph_check.c`, `kgraph_cost.c`, `kgraph_store.c`, `kgraph_band.c`
- `kgraph_map_bd.c`, `kgraph_map_cp.c`, `kgraph_map_df.c` (core loop), `kgraph_map_ex.c`,
  `kgraph_map_fm.c` (gain/migration and PartAdd paths; the 1.8k-line move engine was skimmed, not line-traced),
  `kgraph_map_ml.c`, `kgraph_map_rb.c`, `kgraph_map_rb_map.c`, `kgraph_map_rb_part.c`, `kgraph_map_st.c` (select handling)
- `mapping.c/.h`, `mapping_check.c`, `mapping_io.c`
- `wgraph.c/.h`, `wgraph_check.c`, `wgraph_part_es.c`, `wgraph_part_fm.c` (main loop + rollback), `wgraph_part_ml.c`, `wgraph_part_rb.c`, `wgraph_part_st.c`, `wgraph_part_zr.c`, `wgraph_store.c`
- For contracts only: `library_graph_map.c`, `library_graph_part_ovl.c`, `graph_induce.c` (vnumtax semantics), `src/check/test_scotch_graph_map*.c`, `test_scotch_graph_part_ovl.c`

Interface-layer bugs already reported by other analysts (rename table, `contextOptionSetNum`) are not re-reported.

## Architecture

**Mapping** (`mapping.h:109-120`) is a pair (`parttax`, `domntab`): `parttax[v]` is an index into `domntab`, an array of `ArchDom` architecture (sub)domains, `domnnbr`/`domnmax` counted in domains. `mapBuild()` (`mapping.c:406`) converts a user terminal-number array into this form by hashing terminal numbers, creating domains **in order of first appearance**; `mapTerm()` converts back (`archDomNum` per vertex). `~0`/`-1` in a terminal array means "unknown" and is skipped (`mapping.c:371`).

**Kgraph** (`kgraph.h:110-131`) wraps a Graph plus: current mapping `m`, a *remapping* substructure `r` (old mapping `r.m`, edge coefficients `crloval`/`cmloval`, per-vertex migration costs `r.vmlotax`), fixed-vertex data (`vfixnbr`, `pfixtax`, entries `-1` = free, `>= 0` = fixed terminal), frontier (`frontab`/`fronnbr`), and per-domain load arrays `comploadavg`/`comploaddlt` (always co-allocated; several routines memset across both as one block, e.g. `kgraph.c:198`).

**Two RB paths** (`kgraph_map_rb.c:157`): `archPart(arch)` (complete-graph-like architectures) selects `kgraphMapRbPart` — a context-splitting, possibly multithreaded DFS recursion; otherwise `kgraphMapRbMap` — a job-pool DRB with priority policies and two domain arrays swapped per level. Fixed vertices are stripped before RB (`kgraphMapRbVfloBuild` builds an induced subgraph and per-terminal fixed-load slots), their loads are propagated down bipartitions via `kgraphMapRbVfloSplit`, and the vertices are merged back into the final mapping by `kgraphMapRbVfloMerge`. External gains (previous bipartitions, fixed neighbors, remapping/migration) are folded into each Bgraph by `kgraphMapRbBgraph` (`kgraph_map_rb.c:557-747`); migration gain uses `cmloval * vmlotax[v] * archDomDist(old domain, candidate domain)` and is only applied when `oldmap.parttax[v] != -1` (`:700-714`).

**Direct k-way path**: `kgraphMapMl` coarsens (`graphCoarsen` matching restricted by old parts and pfixtax), carries `pfixtax`, old parts and summed `vmlotax` to the coarse graph (`kgraph_map_ml.c:119-203`), and refines on uncoarsening via strategy (typically band `bd` wrapping diffusion `df` and k-way FM `fm`, plus load exactifier `ex`). `kgraphBand` (`kgraph_band.c`) extracts a band around the frontier and adds one *anchor* vertex per domain carrying the load of all out-of-band vertices of that part (flag `KGRAPHHASANCHORS`); fixed vertices are excluded from the band, their edges being redirected to the anchors of their fixed domains. `kgraphMapBd` runs the strategy on the band graph and merges parts and frontier back, with an early bail-out when an anchor has no edges while its part is non-empty (`kgraph_map_bd.c:158-173`).

**Remapping/repartitioning**: `graphMapCompute2` (`library_graph_map.c:148`) turns `emraval` into an integer `cmloval/crloval` pair (×100, reduced by gcd, `:260-264`), builds `r.m` from the user's `parotab` via `mapBuild` on a `-1`-preset incomplete mapping (`:275-290`). Migration cost is charged by RB (`kgraphMapRbBgraph`), by k-way FM (`kgraphMapFmPartAdd`, via `archDomIncl`/`archDomDist` against `mapDomain(&r.m, v)`), and by diffusion (`kgraphMapDfLoop`, see finding 3).

**Wgraph (vertex-overlap partitioning)** (`wgraph.h:61-72`): `parttax[v] ∈ [0, partnbr)` or `-1` for separator vertices; each part's `compload`/`compsize` counts its own vertices *plus every adjacent separator vertex once* (`wgraphCost`, `wgraph.c:166-228`). Methods: `rb` (recursive vertex-separator bisection using vgraph separators, threaded via context splitting), `ml` (multilevel), `fm` (separator-based FM with save/rollback), `es` (partition via kgraph on a complete arch, then turn kgraph frontier into overlap separator), `zr` (all in part 0). `graphInducePart` composes `vnumtax` through parents (`graph_induce.c:353-355`), so all recursion levels write top-level indices directly — verified sound in both `wgraphPartRb3*` and `kgraphMapRbPart3`.

## Code-quality observations

- `kgraph_map_rb_map.c:916-917`: duplicated statement `pooldat.jobtab[0].vflotab = vflotab;` twice. Harmless.
- `wgraph_part_fm.c:857-858`: debug leftover in the production path:
  `if (savedat.savenbr >= savedat.savesiz) fprintf (stderr, "OUCH\n");` — prints instead of failing/resizing; the neighboring branch relies on `SCOTCH_DEBUG_WGRAPH2`-only bounds checks.
- `kgraph_map_bd.c:268-271`: on `memAlloc` failure the routine returns without `memFree(bndvnumtax…)`/`kgraphExit(&bndgrafdat)` — leak on error path (other error paths in the same function clean up).
- `mapping_io.c:151-157`: `mapLoad` returns on bad input without freeing `mapptab` (group leader). `mapping_io.c:232`: `(Anum) (parttax != NULL) ? … : -1` — cast binds to the condition, not the ternary; semantically identical here but clearly not what was written intentionally. The function carries `/* TODO remove it */`.
- Fixed-vertex sentinel convention drifts across files: `>= 0` = fixed (`kgraph_map_rb.c:261`, `kgraph_map_fm.c:502`), `!= -1` = fixed (`kgraph_band.c:298,313`, `kgraph_map_bd.c:322`, `library_graph_map.c:385`), and `kgraphCheck` requires free vertices to be exactly `-1` (`kgraph_check.c:139-143`). Consistent only if callers use exactly `-1`; see finding 5.
- `SCOTCH_graphPartOvl` (`library_graph_part_ovl.c:110-120`) never initializes `parttab`, `compload`, `fronnbr` before running the strategy: an empty strategy (`STRATNODEEMPTY`) or a leading select (`|`) saves/returns uninitialized data (`wgraphPartSt` STRATNODESELECT saves the "initial partition" first, `wgraph_part_st.c:255`). `wgraphPartZr` also reads `compsize[0]` before anything initialized it (`wgraph_part_zr.c:82`). Default strategies start with `m`/`r` which initialize state at the coarsest level, so this only bites hand-written strategies.
- Threading in `kgraphMapRbPart3` resizes the shared `domntab` under the mapping mutex, and the Part path never reads `domntab` concurrently (VEEXMAPP gains are disabled for `archPart` architectures in `kgraphMapRbBgraph:595`), so the design is consistent — but the safety argument is implicit and fragile.

## Findings

### 1. `kgraph_cost.c:150-154` — anchor-load compensation is dead code (missing `break`)

```c
for (domnnum = 0; domnnum < domnnbr; domnnum ++)
  if ((grafptr->s.verttax[vertancnnd + domnnum + 1] - grafptr->s.verttax[vertancnnd + domnnum]) != 0)
    continue;

if (domnnum != domnnbr) {
```

The loop body is `if (…) continue;` with nothing after it, so the loop always runs to completion and `domnnum == domnnbr` afterwards; the guarded block (`:155-171`), which pins `comploadavg` of zero-degree anchor domains to the anchor's own load and removes them from the proportional balance computation, can never execute. Intended shape is visible in `kgraph_map_bd.c:158-165`, the analogous scan *with* a `break`. Mechanism of impact: for band graphs (`KGRAPHHASANCHORS`) where some anchor has no edges (a part absent from the band, e.g. empty parts during repartitioning or heavily fixed configurations), balance targets `comploadavg`/`comploaddlt` are computed proportionally over all domains including unreachable ones, so band refinement (`fm`/`df`) optimizes against wrong targets. `kgraphMapBd` bails out only when a degree-0 anchor belongs to a *non-empty* part, so the empty-part case does reach this code. Confidence: **high** that the code is dead and a `break` was intended; **medium** on practical severity (quality, not crash).

### 2. `kgraph_band.c:267` — anchor old-part initialization sized by the wrong domain count

```c
memSet (bandparotax + bandvertnbr - bandgrafptr->r.m.domnnbr, ~0, bandgrafptr->r.m.domnnbr * sizeof (Gnum)); /* Old parts of anchors are unspecified */
```

The band graph has `domnnbr = grafptr->m.domnnbr` anchor vertices (current-mapping domains), placed at the *last `domnnbr`* slots; the memSet clears the last `r.m.domnnbr` slots (old-mapping domain count, set at `kgraph_band.c:222` from `grafptr->r.m.domnnbr`). Whenever the old mapping has fewer distinct domains than the current mapping — e.g. `SCOTCH_graphRemap` from an old partition that uses fewer parts than the target (going from 2 old parts to 8, or an initial "everything in part 0" partition) — the first `domnnbr - r.m.domnnbr` anchors keep uninitialized malloc content as their old part. Non-anchor slots are all overwritten by the per-vertex loops (`:352`, `:450`), so only anchors are affected. Consequence chain: k-way FM on the band graph treats any value `!= -1` as a known old part and dereferences it, `kgraph_map_fm.c:668-670`:

```c
if ((parotax != NULL) &&                        /* If we are doing a repartitioning        */
    (parotax[oldvertnum] != -1))                /* And if vertex was mapped to an old domain */
  vexxtab[vexxidx].domoptr = mapDomain (&grafptr->r.m, oldvertnum);
```

`mapDomain` is `&r.m.domntab[parotax[v]]` (`mapping.h:162`) — an out-of-bounds read of the old domain array with a garbage index, then `archDomIncl`/`archDomDist` on the resulting bogus `ArchDom` (`:766-770`): wrong migration gains at best, crash at worst. Anchors do enter FM's hash table (they are ordinary neighbors of last-level band vertices; FM has no anchor special-casing). The band+FM combination is on the **default** mapping strategy (`library_graph_map.c:676`: `asc=b{bnd=d{…}f{…},…}`), so default-strategy `SCOTCH_graphRemap`/`Repart` with a narrower old partition hits this. The bundled test never covers it: its `parotab` is always a full previously-computed mapping (see Test coverage). Fix would be `memSet` over the last `domnnbr` slots. Confidence: **medium-high** (mechanism verified end-to-end in source; not executed).

### 3. `kgraph_map_df.c:353, 388, 439` — diffusion compares old-mapping domain indices with current-mapping part indices

```c
if (difotax[vertnum].partval == parotax[vertend])   /* :353 */
…
if (sorttab[partnum].partval == parotax[vertnum]) { /* :388, soplval */
…
if (parotax[vertnum] == sorttab[0].partval) {       /* :439 */
```

`difotax[].partval`/`sorttab[].partval` are indices into the *current* mapping's `domntab` (initialized from `m.parttax`, `kgraph_map_df.c:246`), while `parotax = grafptr->r.m.parttax` (`:153`) holds indices into the *old* mapping's `domntab`, whose numbering comes from `mapBuild`'s order-of-first-appearance hashing of the user's `parotab` (`mapping.c:374-394`). The two index spaces coincide only by accident (even for `archCmplt`, RB numbers current domains in recursion order and `mapBuild` numbers old domains in first-appearance order). Everywhere else migration is computed properly through architecture domains (`kgraphMapRbBgraph`, `kgraphMapFmPartAdd` use `mapDomain` + `archDomIncl`/`archDomDist`); diffusion alone uses raw index equality, so migration liquid (`mdisval`/`mdidval`, `soplval`) is credited to wrong parts in general remapping runs, including the default strategy (`bnd=d{pass=40}f{…}`). Impact is solution quality of remapping (migration cost modeling), not memory safety — the subsequent FM pass uses correct accounting. Confidence: **medium** — the code is unambiguous, but I cannot exclude an intentional approximation relying on an index-correspondence invariant I did not find; worth asking upstream.

### 4. `kgraph_store.c:126-144` — select-strategy save buffers can be overrun in release builds

`kgraphStoreInit` sizes the save area with `grafptr->m.domnmax` *at init time* (`:81-88`). `kgraphMapSt`'s `STRATNODESELECT` allocates both stores before running either branch (`kgraph_map_st.c:320-330`); a branch may then grow `domnnbr`/`domnmax` (variable-sized architectures grow domains per bipartition, `kgraphMapRbMapPoolResize`; `kgraphMapRbVfloMerge` also resizes). `kgraphStoreSave` guards `domnnbr > storptr->domnmax` only under `SCOTCH_DEBUG_KGRAPH2` (`:126-131`); in release it `memCpy`s `domnnbr` domains/loads into the smaller buffer — heap overflow. Reachable with a user strategy containing `|` on a variable-sized architecture (initial `domnmax` is `MIN(1023, vertnbr)+1`, `mapping.c:105-108`, while domains can grow toward `vertnbr`). Not reachable with fixed-size architectures (`domnnbr ≤ archDomSize < domnmax`). Confidence: **medium** (bound analysis from source; requires an uncommon strategy/architecture combination).

### 5. Library boundary: fixed/old part arrays tolerate only exactly `-1` as "free/unknown", but this is neither checked nor consistently applied

- `SCOTCH_graphRemapFixedCompute` counts `pfixtab[vertnum] != ~0` as fixed (`library_graph_map.c:385`), while `kgraphMapRbVfloBuild` keeps only `>= 0` out of the induced subgraph (`kgraph_map_rb.c:261-282`). A value like `-2` is counted in `vfixnbr` but kept as a free vertex, so `graphInducePart(orggrafptr, …, vertnbr - vfixnbr, …)` is called with an inconsistent vertex count → corrupted induced graph, no error in release builds. Debug validation (`library_graph_map.c:238-244`) only checks entries `>= 0`.
- `mapBuild3` skips only `termnum == ~0` (`mapping.c:371`) and passes any other negative old-part value to `archDomTerm` with the return value ignored (`mapping.c:389`) → garbage domain in `r.m.domntab`, later fed to `archDomDist`.

Mechanism: garbage-in-garbage-out without diagnostics, in release builds only. Confidence: **high** on behavior, **low** on it being a Scotch bug per se (documented behavior is "-1 means free"); reported chiefly because it defines the PyScotch input-validation contract.

### 6. No new findings in: `mapping.c` core (build/merge/term hashing verified, including resize-under-iteration in `mapBuild3`), `kgraph_map_rb_part.c`/`kgraph_map_rb_map.c` (pool pointer-relocation logic in `kgraphMapRbMapPoolResize` verified, including the tied-pool and dummy-link cases), `kgraphMapRbVfloSplit` two-pointer partitioning (both fixed and variable-arch variants), `kgraph_map_ml.c` (comploadavg ownership transfer through the recursion is subtle but correct on success paths; on *error* mid-recursion `finegrafptr->comploadavg` can be left dangling after a coarse-level `memReallocGroup` moved it — but every such path aborts the whole mapping), `kgraph_map_ex.c`, `kgraph_map_cp.c`, `wgraph_part_rb.c`, `wgraph_part_ml.c` (fronload conservation through uncoarsening verified), `wgraph_store.c` (offsets recomputed consistently on restore), `wgraph.c`, `wgraph_check.c`, `kgraph_check.c`.

## Test coverage

`src/check/test_scotch_graph_map.c` exercises 2 strategies × 4 architectures (cmplt, mesh2, oversized mesh2, vhcub) × 7 call types (map, mapFixed, remap±vmlo, remap with one `-1` old entry, remapFixed±vmlo). Gaps:

- **Return-code-only**: `o != 0` is the only assertion (`:228-231`). Nothing verifies that fixed vertices stay in their prescribed terminals, that output parts are valid terminals, balance, or migration behavior. A regression that silently unfixes vertices or corrupts parts would pass.
- The old mapping is always the full mapping computed in case 0 (`memcpy parotab … :207`), so **remapping from an old partition with fewer distinct parts than the target is never exercised** — exactly the shape that triggers finding 2. Case 4 makes a single vertex unknown; partial/unknown-heavy old mappings are untested.
- Only debug builds (`SCOTCH_DEBUG_KGRAPH2`) run `kgraphCheck`/`mapCheck` internally; release CI gets no validity checking at all.

`test_scotch_graph_map_copy.c`: remap with `emraval=0`, no vmlotab, again return-code-only.

`test_scotch_graph_part_ovl.c` recomputes per-part overlap loads and prints min/max/avg (`:157-204`) but asserts nothing about them; it never checks the core overlap invariant (no edge between two distinct non-separator parts). Note `wgraphCheck` itself also does not check that invariant — it validates loads/sizes/frontier membership only (`wgraph_check.c:108-186`) — so even debug builds would accept an "overlap partition" whose parts touch directly. No wgraph test exercises `fm` with a pre-existing frontier or the `es` method.

Nothing tests `SCOTCH_graphRepart`/`RepartFixed` specifically (they are thin wrappers, but the fixed+remap+band+df combination of findings 1-3 is uncovered).

## PyScotch relevance

Contracts observed in `library_graph_map.c` / `library_graph_part_ovl.c` for the ctypes wrappers:

- **`SCOTCH_graphMap`/`graphPart`**: `parttab` is pure output; input values ignored. Passing `parttab=NULL` to `graphMapInit` makes Scotch allocate and zero its own array (`:103-112`), useless through `SCOTCH_graphMap`.
- **`*Fixed` variants**: `parttab` is **in/out**. Input: `-1` = free, `>= 0` = fixed terminal number (must be valid for the arch). Output: computed terminals; fixed entries preserved. PyScotch should validate that free entries are *exactly* `-1`: any other negative value makes `SCOTCH_graphRemapFixedCompute` count the vertex as fixed (`!= ~0`, `:385`) while the core treats it as free (`>= 0` test) — silent internal inconsistency, no error return (finding 5). If **all** vertices are fixed, the call returns 0 without touching anything (`:246-249`).
- **`SCOTCH_graphRemap`/`Repart`**: `parotab` is input-only (old terminal numbers, `-1` = unknown; again, enforce exactly `-1`). `parttab` is output-only for the non-Fixed variants — its input values are *not* read. `emraval` is quantized to 1/100ths (`(INT)(emraval*100.0+0.5)` then gcd-reduced, `:261-264`); negative `emraval` is not rejected and yields a negative migration coefficient — PyScotch should reject `emraval < 0` itself.
- **`vmlotab`**: read-only, `vertnbr` entries, only consulted when an old mapping is present (`:260`); with `vmlotab=NULL` every vertex has migration cost 1. There is no size check anywhere — a short array is a silent OOB read; PyScotch must enforce `len == vertnbr`.
- **`SCOTCH_graphPartOvl`**: `parttab` is output-only; values `0..partnbr-1`, `-1` for separator ("overlap") vertices. Callers must expect `-1`s (the hypothesis tests should assert the overlap invariant themselves, since neither Scotch's checker nor its test does — see above). Do not pass an empty strategy: `parttab` would be returned uninitialized.
- Given findings 1-3, PyScotch hypothesis tests around **remapping where the old partition uses fewer distinct parts than the target count** (and around fixed-vertex remap on band-refined strategies) are the highest-value additions; they cover territory the upstream tests provably do not, and finding 2 predicts garbage-dependent nondeterminism (or crashes under ASan) precisely there.
