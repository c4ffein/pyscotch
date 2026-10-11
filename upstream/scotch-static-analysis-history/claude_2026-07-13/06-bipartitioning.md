# Bipartitioning — Scotch v7.0.11

## Scope

Reviewed the 14 `bgraph_*` files under `/home/dev/workspace/pyscotch/external/scotch/src/libscotch/` (all line references below are relative to that directory):

- Core: `bgraph.c` / `bgraph.h` (structure, init/exit/swal/zero), `bgraph_check.c` (invariant checker), `bgraph_cost.c` (cost recomputation), `bgraph_store.c` (save/restore for strategy selection).
- Methods: `bgraph_bipart_bd.c` (band), `bgraph_bipart_df.c` (diffusion), `bgraph_bipart_ex.c` (exact-balance), `bgraph_bipart_fm.c` (Fiduccia–Mattheyses, deep-read), `bgraph_bipart_ga.c` (genetic), `bgraph_bipart_gg.c` (greedy graph growing), `bgraph_bipart_gp.c` (Gibbs–Poole–Stockmeyer growing), `bgraph_bipart_ml.c` (multilevel), `bgraph_bipart_st.c` (strategy interpreter), `bgraph_bipart_zr.c` (zero).

Cross-checked against the `vgraph_separate_fm.c` twin, `kgraph_map_rb.c` (which builds the Bgraphs and `veextab`), `library_graph_map.c` (default strategy strings), and upstream git history (v6.0.5 blob `35b98f9`, tags v7.0.11/v7.0.12 — HEAD is contained in both, so all findings below persist in 7.0.12).

## Architecture

### Bgraph invariants (enforced by `bgraphCheck`, debug builds only)

- `parttax[v] ∈ {0,1}`; `frontab[0..fronnbr)` lists exactly the vertices having at least one neighbor in the other part, without duplicates (`bgraph_check.c:109-173`).
- `compload0` is the **movable** vertex load of part 0: `compload0 == velosum − load(part 1)` (`bgraph_check.c:182`). Fixed-vertex loads are *not* included in `compload0`; they are folded into the target instead:
  `compload0avg == ⌊(velosum + vfixload[0] + vfixload[1]) · domnwght[0] / (domnwght[0]+domnwght[1])⌋ − vfixload[0]` (`bgraph_check.c:98-99`, mirrored by `bgraphInit2`, `bgraph.c:159`).
- `compload0 == compload0avg + compload0dlt` (`bgraph_check.c:104`).
- `commload == domndist · (internal cut load) + commloadextn0 + Σ_{v∈part1} veextax[v]` and `commgainextn == Σ_v (1 − 2·part(v)) · veextax[v]` (`bgraph_check.c:186-192`, computed by `bgraphCost2`).

### veextab (external gains)

`veextax[v]` is the change in external communication if `v` moves to part 1. It is built by `kgraphMapRbBgraph` (`kgraph_map_rb.c:558-747`) from three sources: edges to fixed vertices, mapping distances to already-mapped neighbors (sequential RB), and remapping migration costs. `commloadextn0`/`commgainextn0` record the all-in-part-0 reference so that `bgraphZero`/`bgraphCost` can restart from it. The array is dropped if all entries are zero (`veexmsk` trick).

### FM implementation (`bgraph_bipart_fm.c`)

- Extended vertices live in an open-addressing hash table (linear probing, multiplier `BGRAPHBIPARTFMHASHPRIME = 17`), `~0`-filled slots meaning empty. `hashmax = hashsiz/4`; exceeding it triggers `bgraphBipartFmResize` which doubles the array group, rehashes in two segments (starting after the last empty slot to preserve probe chains), and re-translates the save array via vertex numbers.
- Gain structure is either the logarithmic-bucket `GainTabl` (`SCOTCH_TABLE_GAIN`, the compiled default, `bgraph_bipart_fm.c:80`) or a Fibonacci heap. Vertex state is encoded in `gainlink.next`: `0` free, `1` used/locked, `≥2` linked in table (`bgraph_bipart_fm.h:161-177`).
- Per pass: moves are journaled in `savetab` (first touch per sweep, keyed by `mswpnum`); moved vertices are locked in a linked list (`lockptr`); at pass end the journal is unwound back to the best recorded position. Balance bounds start at the current imbalance and are tightened toward the strategy bounds as improving positions are found (`compload0dltmit/mat` vs `compload0dltmin/max`, lines 292-298 and 686-702).
- When `commgainextn < 0` a **global swap** is evaluated: all parts are virtually flipped (`swapval`), external gains change sign, and only hash-resident vertices need gain fixups (lines 712-781). At exit, if the best position has `swapvalbst != 0` the whole `parttax` is flipped before hash-resident parts are written back (lines 796-833).
- If the frontier is empty and the balance is off, FM first runs `bgraphBipartGg` and switches to all-vertices mode (lines 302-318) — the only way `typeval` ever becomes `BGRAPHBIPARTFMTYPEALL` (see finding F4).

### Multilevel and strategy selection

- `bgraphBipartMl2` (`bgraph_bipart_ml.c:313-335`) recurses: `graphCoarsen` (external gains merged per multinode), recursive call, `bgraphBipartMlUncoarsen` (parts propagated per multinode; the coarse frontier array is the fine one recycled in place; split multinodes append the second vertex at the end), then the ascending strategy. When coarsening fails (threshold reached), `bgraphBipartMlUncoarsen(grafptr, NULL, NULL)` calls `bgraphZero` and the low strategy runs. Imbalance bounds are widened per level by `(levlnum+1) + 5%` of the margin (`bgraph_bipart_ml.c:148-152`).
- `bgraphBipartSt` interprets strategies: concatenation, conditions (`bal`, `edge`, `levl`, `lmin0`, `lmax0`, `load`, `load0`, `vert`), selection `|` (both branches run from a `BgraphStore` snapshot; the balanced one wins, ties broken on `commload` then `|compload0dlt|`, `bgraph_bipart_st.c:326-381`), and the method table `b`=bd, `d`=df, `x`=ex, `f`=fm, `a`=ga, `h`=gg, `g`=gp, `m`=ml, `z`=zr (`bgraph_bipart_st.c:128-138`).
- Default sequential strategies (`library_graph_map.c:676-736`) use `m` (with `low=h…f`, `asc=b{bnd=(d{pass=40}|)f…, org=f…}`) and `x`+`f` when `SCOTCH_STRATBALANCE`. So **bd, df, ex, fm, gg, ml are reachable from default strategies; ga, gp, zr only via user strategy strings** (and `zr` also via `bdgraph_gather_all.c:198`).

## Code-quality observations

- `bgraphSwal` (`bgraph.c:212-231`) has no callers anywhere in `src/` (only the rename entry in `module.h:720`) — dead code, and its arithmetic disagrees with `bgraphCheck` when `vfixload != 0` (same inconsistency as finding F5).
- `bgraph_bipart_bd.c:395-396`: `bndedlosum += bndedloval;` in the anchor-edge fill loop is dead — `s.edlosum` was already stored at line 374, and the correct 2× accounting was completed at line 361 (`bndedlosum += ancedloval; /* Account for anchor edges a second time */`). If anything ever re-read `bndedlosum` after line 396 it would be wrong (anchor arcs counted 3×). Misleading.
- `bgraph_bipart_ga.c:178`: `randnbr = MIN (sizeof (UINT), partnum);` — bytes vs bits confusion: only `sizeof(UINT)` (8) of the 64 random bits per draw are consumed. Wasteful, not incorrect.
- `bgraph_bipart_ga.c:65`: a commented-out `//#define BGRAPHBIPARTGANOTHREAD` after the includes, plus C++-style comment, in an otherwise strictly C89-commented codebase — signals the method's experimental status.
- Debug-only error paths in `bgraphBipartBd` (`bgraph_bipart_bd.c:158, 193, 300, …`) `return (1)` without freeing `queutab`/band structures — leaks, but only under `SCOTCH_DEBUG_BGRAPH2`.
- `bgraph_bipart_bd.c:430`: the shrinking `memRealloc` of the edge array is not checked for NULL.
- Many hot loops rely on the `TRICK` idioms (`partmsk = -partval`, `edloptr -= edlomsk` with `~0 == -1`); these are correct but assume two's complement and make the twins (`fm`/`gg`/`gp` vs their vgraph/kgraph counterparts) diverge textually, which is exactly where F3/F10 crept in.

## Findings

### F1 — df: anchor re-injection doubled, external-gain feedback to anchors dropped (v7 regression)

- **Where**: `bgraph_bipart_df.c:380`
- **Excerpt**:
  ```c
  vancval = loopptr->vanctab[vertnum - vancnnd] + loopptr->vanctab[vertnum - vancnnd]; /* Load variable with anchor value */
  ```
- **Mechanism**: the per-pass contributions of regular vertices' external gains to the two anchors are accumulated in `vancval0/vancval1`, stored to `loopptr->thrdtab[thrdnum].vanctab[0/1]` and reduced across threads (`bgraph_bipart_df.c:367-373`, root = `thrdlst`) — and then never used. The anchor load should be `loopptr->vanctab[i] + loopptr->thrdtab[thrdlst].vanctab[i]`; v6.0.5 had exactly that (`bgraph_bipart_df_loop.c:302` in blob `35b98f9`: `loopptr->vanctab[…] + thrdptr->vanctab[…]`). As written, the injected anchor value is added to itself (2×) and the veex feedback term is discarded. Introduced by commit `67c0d61` ("Apply new thread model to bgraphBipartDf()"); still present at v7.0.12.
- **Impact**: with `veextax == NULL` (plain partitioning) the anchor injections are doubled — not a pure scaling because the per-vertex `±velfval` subtraction (lines 346-355) is not scaled, so diffusion results differ from the intended algorithm. With `veextax != NULL` (mapping/remapping/fixed vertices) the mapping feedback to anchors is silently lost. `d{pass=40}` sits inside the **default** sequential strategies (band refinement, `library_graph_map.c:684-685`), though always under a selection `(d{...}|)`, so degraded df results are filtered against the pre-df partition — quality loss, never inconsistency.
- **Confidence**: high (verbatim v6 diff; the reduced values are provably dead).

### F2 — FM: missing `return` after failed hash-table resize → use-after-free + double free

- **Where**: `bgraph_bipart_fm.c:598-604`
- **Excerpt**:
  ```c
  if (hashnbr >= hashmax) {             /* If extended vertex table is already full */
    if (bgraphBipartFmResize (&hashtab, &hashmax, &hashmsk, &savetab, savenbr, tablptr, &lockptr) != 0) {
      errorPrint ("bgraphBipartFm: out of memory (2)");
      memFree    (hashtab);             /* Free group leader */
      bgraphBipartFmTablExit (tablptr);
    }
    for (hashnum = (vertend * BGRAPHBIPARTFMHASHPRIME) & hashmsk; hashtab[hashnum].vertnum != ~0; hashnum = (hashnum + 1) & hashmsk) ; /* Search for new first free slot */
  }
  ```
- **Mechanism**: on resize failure the group leader `hashtab` is freed and the gain table destroyed, but there is **no `return (1)`** — execution falls through into the probe loop, reading and then writing the freed allocation, continues the whole pass, and frees `hashtab` a second time at line 849 before returning 0 (success). The twin `vgraph_separate_fm.c:589-590` has the `return (1)`.
- **Impact**: heap corruption / double free, but only on the memory-exhaustion path. Long-standing (identical in 6.0.5, lines 598-603).
- **Confidence**: high (control flow is unambiguous; trigger requires OOM).

### F3 — FM: `partval == 2` in backtrack loop is dead code copied from the vertex-separator FM; boundary vertices leak out of the gain table between passes

- **Where**: `bgraph_bipart_fm.c:479-484`
- **Excerpt**:
  ```c
  if (bgraphBipartFmIsTabl (&hashtab[hashnum])) {       /* If vertex is linked */
    bgraphBipartFmTablDel (tablptr, &hashtab[hashnum]); /* Unlink it           */
    bgraphBipartFmSetFree (&hashtab[hashnum]);          /* Set it as free      */
  }
  if (bgraphBipartFmIsFree (&hashtab[hashnum]) && (partval == 2)) /* If vertex not locked and in separator */
    bgraphBipartFmTablAdd (tablptr, &hashtab[hashnum]); /* Re-link it                                      */
  ```
- **Mechanism**: in bipartitioning, `partval` (restored from `savetab`) is always 0 or 1, so the re-link condition is never true. The code and comment are copied from `vgraph_separate_fm.c:329`, where part 2 means "in separator"; the bgraph analog of "in separator" is `commcut > 0`. Consequence: at the start of each pass, when the journal is unwound past the best position, every *touched-but-not-moved* boundary vertex is unlinked from the gain table and never re-added (the lock-list loop at lines 501-511 only re-adds *moved* vertices). Such vertices can only re-enter the table if a later move touches them again as neighbors (lines 580-587).
- **Impact**: the gain table silently depletes across passes, so multi-pass FM explores fewer candidates than designed — refinement quality only; all published graph state stays consistent (`bgraphCheck` passes). Long-standing (identical in 6.0.5, line 481).
- **Confidence**: high that the branch is dead and diverges from the twin's semantics; medium on the magnitude of the quality effect.

### F4 — FM ignores its `typeval` parameter; `x` (bgraphBipartEx) cannot request all-vertices mode

- **Where**: `bgraph_bipart_fm.c` (whole routine) vs `bgraph_bipart_fm.h:93` and `bgraph_bipart_ex.c:103`
- **Excerpt** (`bgraph_bipart_ex.c:100-104`):
  ```c
  parafmdat.movenbr = grafptr->s.vertnbr;
  parafmdat.passnbr = ~0;
  parafmdat.deltval = 0.0L;                       /* Exact balance required */
  parafmdat.typeval = BGRAPHBIPARTFMTYPEALL;      /* All vertices involved  */
  ```
- **Mechanism**: `bgraphBipartFm` reads `paraptr->deltval`, `movenbr`, `passnbr` (lines 292, 323, 460, 517) but **never `paraptr->typeval`**. The local `typeval` is hard-set to `BGRAPHBIPARTFMTYPEBOUNDARY` (line 300) and only becomes `ALL` internally when the frontier is empty (line 316). So the strategy parameter `f{type=a}` (parsed via the `"ab"` case table, `bgraph_bipart_st.c:173-176`) and Ex's explicit request are silently ignored. Ex — used by default strategies under `SCOTCH_STRATBALANCE` (`library_graph_map.c:689`) — is documented as moving all vertices to reach exact balance; with a non-empty frontier it only gets boundary moves, so it can fail to restore balance in configurations where the needed vertices are interior.
- **Impact**: strategy parameter without effect; weaker exact-balancing than designed. Long-standing (6.0.5 identical).
- **Confidence**: high (grep-verifiable); medium for practical impact (boundary moves plus Ex's imbalanced-fallback to Gg cover many cases).

### F5 — `bgraphZero` contradicts the `bgraphCheck` invariant when fixed-vertex loads are present

- **Where**: `bgraph.c:246-249` vs `bgraph_check.c:182` / `bgraph.c:159-161` (`bgraphInit2`) / `bgraph_cost.c:171`
- **Excerpt** (`bgraph.c:246-249`):
  ```c
  compload0 = grafptr->s.velosum + grafptr->vfixload[0];
  grafptr->fronnbr      = 0;                      /* No frontier vertices */
  grafptr->compload0dlt = compload0 - grafptr->compload0avg;
  grafptr->compload0    = compload0;
  ```
  vs `bgraph_check.c:182`: `if ((grafptr->s.velosum - cpl1sum) != grafptr->compload0)`.
- **Mechanism**: `bgraphInit2`, `bgraphCost` and `bgraphCheck` define `compload0` as the *movable* load of part 0 (all-in-0 ⇒ `compload0 == velosum`). `bgraphZero` (rewritten in the 6.0.1 import, per `git log -L`) sets `compload0 = velosum + vfixload[0]`, overstating `compload0`/`compload0dlt` by `vfixload[0]`. `vfixload` is nonzero exactly when fixed vertices exist (`kgraphMapRbVfloSplit` computes the per-subdomain fixed loads passed as `vflowgttab`, `kgraph_map_rb.c:323+`). `bgraphZero` is reached from `bgraph_bipart_zr.c:84`, `bgraph_bipart_gp.c:107`, and — critically — from `bgraph_bipart_ml.c:209` at the **coarsest level of every multilevel bipartitioning**, which default strategies always use. `bgraphSwal` has the same skew (`bgraph.c:225-227`) but is dead code.
- **Impact**: with `SCOTCH_graphMapFixed`-style inputs, every bipartitioning job starts its coarsest-level refinement from a `compload0dlt` biased by `vfixload[0]`, so balancing decisions target the wrong deficit (the bias survives because all methods update `compload0dlt` incrementally); under `SCOTCH_DEBUG_BGRAPH2`, `bgraphCheck` fails ("invalid part load") right after `bgraphBipartMlUncoarsen`. (`gp` is unaffected in practice: it recomputes `compload0dlt` from scratch at line 120.)
- **Confidence**: high that the two formulas are mutually inconsistent (they cannot both hold when `vfixload[0] != 0`); medium on which side upstream considers canonical — but `bgraphCheck`+`bgraphCost`+`bgraphInit2` outvote `bgraphZero` 3:1.

### F6 — ga: division by zero (SIGFPE) on 2-vertex graphs

- **Where**: `bgraph_bipart_ga.c:239` with guard at `bgraph_bipart_ga.c:293`
- **Excerpt**:
  ```c
  if (grafptr->s.vertnbr < 2)                     /* If less than two vertices, no crossing-over possible ... */
    return (0);
  ...
  vecridx = 1 + contextIntRandVal (grafptr->contptr, vertnbr - 2); /* Crossing-over preserves at least one vertex in each segment */
  ```
- **Mechanism**: `intRandVal` is a bare modulo (`common_integer.c:458`: `return (((UINT) intRandVal3 (...)) % randmax);`). For `vertnbr == 2` the guard passes and `randmax == 0` → integer division by zero. Any strategy containing method `a` applied to a 2-vertex bgraph (e.g. `m{low=a...}` reaching a tiny coarsest graph, or recursive bipartitioning of a tiny subgraph) crashes the process.
- **Impact**: hard crash (SIGFPE), but `a` is not in any default strategy — only crafted strategy strings reach it.
- **Confidence**: high.

### F7 — ga: unsynchronized shared PRNG across threads

- **Where**: `bgraph_bipart_ga.c:177, 239, 246` in the threaded `bgraphBipartGaLoop`, with `common.h:508` (`contextIntRandVal(c,n) → intRandVal((c)->randptr,(n))`) and the xorshift state update in `common_integer.c:421-435`.
- **Mechanism**: every worker thread launched by `contextThreadLaunch` (`bgraph_bipart_ga.c:310`) draws from the single `IntRandContext` of the execution context with no lock; `intRandVal3` performs read-modify-write on `randtab[0..1]`. This is a C11 data race.
- **Impact**: ga results are nondeterministic even with a fixed seed (`SCOTCH_randomReset`) and a fixed thread count; torn state is harmless statistically but undefined behavior formally. No other bgraph method draws random numbers inside a threaded region (gg/gp draw on the calling thread; df's threaded loop uses none).
- **Confidence**: high for the race; ga is explicitly experimental.

### F8 — df: OOM abort path publishes uninitialized results

- **Where**: `bgraph_bipart_df.c:207-213` (abort set), `bgraph_bipart_df.c:280-284` (early return), `bgraph_bipart_df.c:519-525` (consumption)
- **Excerpt** (`bgraph_bipart_df.c:519-520`):
  ```c
  grafptr->fronnbr      = loopdat.thrdtab[thrdlst].fronnnd[0]; /* Get data after scan-reduction */
  grafptr->compload0    = grafptr->s.velosum - loopdat.thrdtab[thrdlst].compload1[0];
  ```
- **Mechanism**: if any thread fails its local allocation it sets `loopptr->abrtval = 1` and *all* threads return right after the first barrier — before the statistics scan at lines 441-449 ever writes `thrdtab`. `thrdtab` comes from `memAllocGroup` (line 492) and is never zero-initialized, so `bgraphBipartDf` then copies garbage into `fronnbr`, `compload0`, `compload0dlt`, `compsize0`, `commload`, `commgainextn` — and still `return (0)`. A garbage `fronnbr` breaks the frontier invariant for every subsequent method (e.g. FM iterates `frontab[0..fronnbr)`, out-of-bounds reads/writes). The NaN-overflow abort (line 360) is *not* affected — it breaks out of the pass loop but still runs the statistics phase.
- **Impact**: state corruption presented as success, but only on the memory-exhaustion path (same trigger class as F2).
- **Confidence**: high (control flow), low trigger probability.

### F9 — FM: global-swap balance check ignores the lower bound

- **Where**: `bgraph_bipart_fm.c:722-723`
- **Excerpt**:
  ```c
  compload0dlttmp = grafptr->s.velosum - compload0dlt - 2 * grafptr->compload0avg;
  if (abs (compload0dlttmp) <= compload0dltmax) { /* If still within bounds, perform actual swapping */
  ```
- **Mechanism**: the working bounds are the asymmetric interval `[compload0dltmin, compload0dltmax]` (lines 295-298; `compload0dltmin` derives from `compload0min − compload0avg` and can differ in magnitude from `compload0dltmax` whenever `domnwght[0] != domnwght[1]` or the strategy sets asymmetric `compload0min/max`). Comparing `abs(...)` against only `compload0dltmax` accepts swaps with `compload0dlttmp < compload0dltmin` (e.g. min = −10, max = 100, tmp = −50). A subsequent improving position in that state can be recorded as best (lines 760-771), yielding a final partition outside the requested lower balance bound.
- **Impact**: balance-constraint violation in mapping configurations with asymmetric domain weights and external gains (global swap requires `veextax != NULL`). Everything stays internally consistent; only the strategy contract is broken.
- **Confidence**: medium (arithmetic is clear; hitting it needs asymmetric bounds + beneficial swap, which I have not constructed end-to-end).

### F10 — zr: wrong guard with zero-weight vertices (diverges from gp's correct twin)

- **Where**: `bgraph_bipart_zr.c:83` vs `bgraph_bipart_gp.c:106`
- **Excerpt**:
  ```c
  if (grafptr->compload0 != grafptr->s.velosum)   /* If not all vertices already in part zero */
    bgraphZero (grafptr);
  ```
- **Mechanism**: with zero-weight vertices in part 1, `compload0 == velosum` holds while the partition is *not* all-in-0, so `z` silently does nothing (frontier, `compsize0`, `commload` keep their old values). `gp` faces the same question two lines into its routine and tests `compsize0 != vertnbr` (vertex count), which is correct.
- **Impact**: the "zero" method fails its postcondition only for graphs containing zero-load vertices; state remains self-consistent, so nothing crashes downstream. Cosmetic-to-low.
- **Confidence**: high for the divergence; low impact.

### F11 — `abs()` applied to `Gnum` throughout (64-bit builds)

- **Where** (representative): `bgraph_bipart_fm.c:136, 668, 677`; `bgraph_bipart_st.c:364, 370-372`; `bgraph_bipart_gg.c:246, 298`; `bgraph_bipart_ga.c:204, 259`; `bgraph_bipart_fm.c:723`.
- **Mechanism**: there is no Scotch-provided `abs` override (`grep` finds none in `common*.h`/`module.h`), so these calls resolve to C's `int abs(int)`. With `-DINTSIZE64` (`common.h:228-229`, `INT = int64_t` — the build PyScotch uses for its 64-bit variant), arguments are silently narrowed; load deltas whose magnitude exceeds 2³¹ produce wrong comparisons (tie-breaking, balance selection in `|`-selection nodes, gg's growth stop test).
- **Impact**: only graphs whose total vertex load exceeds ~2·10⁹ are affected; then balance decisions are quietly wrong. This is a library-wide pattern, not specific to bgraph.
- **Confidence**: high on the code pattern; low practical frequency.

## Test coverage

`src/check/` contains **no direct bgraph tests**. The only executables that reach the bipartitioning code are end-to-end: `test_scotch_graph_map.c` (default and `SCOTCH_STRATRECURSIVE` strategies, including `graphMapFixedCompute`/`graphRemapFixedCompute`), `test_scotch_graph_map_copy.c`, and `test_scotch_graph_part_ovl.c`. All of them assert only the return code (`if (o != 0) exit(EXIT_FAILURE);`, `test_scotch_graph_map.c:228-231`) — no balance, cut, frontier, or determinism validation. Consequences:

- The real correctness oracle, `bgraphCheck`, is compiled in only with `SCOTCH_DEBUG_BGRAPH2`, and the FM-internal `bgraphBipartFmCheck` needs `SCOTCH_DEBUG_BGRAPH3`; a release-mode test run exercises neither. That is precisely why F5 (which trips `bgraphCheck` immediately under debug flags with fixed vertices) and F1 (pure quality regression) can survive in released versions.
- Methods `a` (ga) and `g` (gp) and `z` (zr) are in no default strategy and therefore have effectively **zero** coverage from `src/check/`.
- df's threaded reduction/scan paths and FM's resize path (`SCOTCH_DEBUG_BGRAPH2` deliberately shrinks `hashnbr` at `bgraph_bipart_fm.c:321` "for maximum code coverage") are exercised only in debug builds.

## PyScotch relevance

- **Reachability**: PyScotch reaches this code through `SCOTCH_graphPart`/`SCOTCH_graphMap` (recursive bipartitioning) and any custom strategy set via `SCOTCH_stratGraphMap`. Default strategies exercise ml/gg/fm/bd/df(/ex); F1 therefore affects the *quality* (never the validity) of default partitions computed by PyScotch on Scotch 7 vs Scotch 6. F3/F4 similarly cap refinement quality. None of these can corrupt results returned to Python in normal operation — the OOM-path findings (F2, F8) are the only state-corruption risks, and they require allocation failure.
- **Determinism**: bipartitioning outcomes depend on the context PRNG (gg root selection `bgraph_bipart_gg.c:220`, permutations at 285; ml's coarsening matchings; ga throughout), confirming the project rule to call `SCOTCH_randomReset()` before each run. Two extra caveats: (1) df sums `float` diffusion values in a thread-count-dependent partitioning, so results vary with `SCOTCH_contextInit` thread counts even with a fixed seed — pin the thread count for reproducible tests; (2) ga is nondeterministic under threads regardless of seed (F7).
- **Caller-violable invariants via strategy strings** (worth guarding or documenting in PyScotch, since strategy strings are user input):
  - `d` (diffusion) requires a graph with anchor vertices; the check exists only under `SCOTCH_DEBUG_BGRAPH1` (`bgraph_bipart_df.c:485-490`). In release builds, a `sep=d{...}` strategy applied outside a band context silently treats the last two vertices as anchors and produces meaningless (though structurally valid) partitions.
  - `a` (ga) crashes with SIGFPE on 2-vertex subgraphs (F6) — reachable from Python by passing a strategy string containing `a` and partitioning small graphs.
  - `z`/multilevel with fixed vertices hits F5; PyScotch's Hypothesis tests comparing `compload` values against manually recomputed loads on `graphMapFixed`-style inputs would detect it (the C tests never will).
  - `f{pass=0}` and `f{pass=-1}` intentionally mean "iterate until no improvement" (`bgraph_bipart_fm.c:784-785`, the `--passnbr != 0` TRICK); not a hang, but surprising semantics worth noting in PyScotch docs.
