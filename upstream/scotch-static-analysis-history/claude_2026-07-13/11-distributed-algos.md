# Distributed algorithms — Scotch v7.0.11

## Scope

Files reviewed under `external/scotch/src/libscotch/` (tag v7.0.11, read-only):

- `bdgraph_*.c` (11 files): distributed edge bipartitioning — `bipart_bd`, `bipart_df`, `bipart_ex`, `bipart_ml`, `bipart_sq`, `bipart_st`, `bipart_zr`, `check`, `gather_all`, `store`.
- `vdgraph_*.c` (10 files): distributed vertex separators — `separate_bd`, `separate_df`, `separate_ml`, `separate_sq`, `separate_st`, `separate_zr`, `check`, `gather_all`, `store`.
- `hdgraph_*.c` (9 files): distributed halo graphs and parallel ordering — `order_nd`, `order_si`, `order_sq`, `order_st`, `fold`, `gather`, `induce`, `check`.
- `kdgraph_*.c` (6 files): distributed k-way mapping — `map_rb`, `map_rb_map`, `map_rb_part`, `map_st`, `gather`.

Depth: line-by-line for `bipart_df/sq/ml/ex/bd`, `separate_df/sq/ml/bd`, `order_nd/sq/si`, `map_rb*`, `gather`, `gather_all`; control-flow skim only for `hdgraph_fold.c` (43 KB point-to-point fold, mirrors `dgraph_fold.c`), `hdgraph_induce.c`, the `*_check/store/zr/st` files. Sequential twins (`bgraph_*`, `vgraph_*`) consulted for divergence checks. Interface-layer issues are out of scope (reported elsewhere).

## Architecture

**Bdgraph (distributed Bgraph).** Same active-graph design as the sequential edge bipartitioner, parallelized as:

- `bipart_ml`: multilevel via `dgraphCoarsen` with fold-dup (`DGRAPHCOARSENFOLDDUP`): below `foldmax` vertices/process, the coarse graph is folded onto each half of the ranks, both halves recurse independently, and at uncoarsening the best of the two candidate partitions is selected by a user `MPI_Op` reduction (`bdgraphBipartMlOpBest`, `bdgraph_bipart_ml.c:181`) keyed on (validity, commload, imbalance), ties broken by lowest rank. A memory-error flag rides in slot `[5]` of the same reduction.
- There is **no distributed FM** (`bdgraph_bipart_fm.c` does not exist). Refinement is delegated to: `bipart_df` (diffusion "jug of the Danaides" on a band graph, the parallel stand-in for FM), `bipart_bd` (build a distributed band graph of width `distmax` around the frontier via `dgraphBand`, apply a sub-strategy to it, project back with last-layer frontier spill recomputation), `bipart_ex` (load exactifier: global gain-bucket `MPI_Allreduce` then per-rank residual moves), and `bipart_sq` (multi-sequential: `bdgraphGatherAll` replicates the whole graph on every rank, each rank runs sequential `bgraphBipartSt` with a deliberately desynchronized RNG, and an `MPI_Op` reduction picks the winner whose partition is then `commScatterv`-ed back).
- Band graphs place exactly two anchor vertices as the last two local vertices of every rank; anchor degrees are reduced globally to detect unusable anchors; last-layer band vertices carry an edge to their part's anchor, which is what makes the post-refinement "anchors kept their parts" check (`bipart_bd.c:247`, `separate_bd.c:159`) sufficient for projection validity.

**Vdgraph.** Same pattern for vertex separators: `separate_ml` (fold-dup + OpBest), `separate_df` (diffusion then separator extraction from the aggregated part), `separate_bd` (band), `separate_sq` (multi-sequential via `vdgraphGatherAll`), `separate_zr`. No distributed vertex-FM either.

**Hdgraph ordering.** `hdgraphOrderNd` is parallel nested dissection: compute a distributed separator with a Vdgraph strategy on the non-halo part; order the separator via non-halo induction; then split the ranks in two halves with `MPI_Comm_split`, induce each part on *all* processes (`hdgraphInduceList`) and either fold it onto its half (`hdgraphFold2`) or, when a half is down to one process, centralize it with `hdgraphGather` into a sequential `Hgraph` handled by `hdgraphOrderSq2`. `order_sq` gathers to rank 0 of the sub-communicator and orders sequentially; `order_si` is the identity leaf. With `SCOTCH_PTHREAD_MPI` + `MPI_THREAD_MULTIPLE`, the two folds run on two threads over a duplicated communicator; otherwise sequentially.

**Kdgraph mapping.** `kdgraphMapRbPart` is parallel dual recursive bipartition: bipartition the current Dgraph with a Bdgraph strategy, split ranks in halves, `dgraphInducePart` + `dgraphFold2` each side (or `dgraphGather` when a side reaches one process, ending in sequential `kgraphMapSt`), recurse. Results accumulate as `DmappingFrag` fragments (`kdgraph_map_rb_map.c`).

**Multi-sequential RNG.** `bdgraphGatherAll`/`vdgraphGatherAll` advance the random generator `2*proclocnum` times and permute the gathered frontier array so each rank's sequential run explores a different solution (`bdgraph_gather_all.c:244-246`, `vdgraph_gather_all.c:208-210`). This is the intended source of rank-dependent nondeterminism.

**Error-handling convention.** Memory errors are made collective only when `SCOTCH_DEBUG_{B,V,H}DGRAPH1` is defined ("Communication cannot be overlapped by a useful one"); in production builds a rank that fails an allocation frequently returns alone while the others enter the next collective — a deliberate performance tradeoff whose failure mode is a hang rather than an error.

## Code-quality observations

- Heavy copy-paste between the `b`/`v` twins with real divergence (findings 1, 2, 8, 9 below). Where the twins agree, the code is careful and idiomatic (TRICK-annotated array recycling, in-place packing in `vdgraphSeparateMlPack`, overlap-aware `memAllocGroup` layouts).
- `memAllocGroup` on failure NULLs **only the first** output pointer (`common_memory.c:508-511`); several error paths rely on testing later pointers or on pointer arithmetic against NULL (`ielsloctax -= baseval` then `!= NULL` test in `bipart_df.c:133/144`). It works by accident for the first pointer and is UB-adjacent; in one place it is outright wrong (finding 4).
- Debug-macro cross-contamination: vdgraph files gate collective error checks on **bdgraph** macros; one bdgraph guard uses the sequential **bgraph** macro (findings 8, 9).
- Error paths routinely leak on MPI failure (`besttypedat`/`bestoperdat`/`cgrfdat` in `bipart_sq.c:203-216`, group leaders in `bipart_df.c:138-141`). Low impact since MPI errors are effectively fatal.
- The overflow state of the diffusion methods (`ovflval`, `bipart_df.c:256-259`) is per-rank and never reset: a rank that hits NaN freezes and only replays halo syncs while the others keep diffusing. No deadlock (syncs stay collective), but the algorithm silently degrades asymmetrically.

## Findings

**1. `bdgraph_bipart_sq.c:207` — post-reduction check reads the local array instead of the reduced one; single-rank bipartition failure hangs the communicator.** High confidence.

```c
if (MPI_Allreduce (reduloctab, reduglbtab, 1, besttypedat, bestoperdat, dgrfptr->s.proccomm) != MPI_SUCCESS) {
  ...
}
if ((reduloctab[4] != 0) && (reduloctab[4] != dgrfptr->s.procglbnbr)) {
  errorPrint ("bdgraphBipartSq: internal error");
  return     (1);
```

The reduction op accumulates the global failure count into slot 4 (`inout[4] += in[4]`, line 97), so the intended check is `reduglbtab[4]` ("some but not all ranks failed"). As written, `reduloctab[4]` is the *local* 0/1 flag: with `procglbnbr > 1`, any rank whose local `bgraphBipartSt` failed satisfies `(1 != 0 && 1 != procglbnbr)` and returns alone, while the healthy ranks (local flag 0) proceed to `MPI_Bcast` (line 231) and `commScatterv` (line 242) → deadlock. If *all* ranks fail, every rank takes this wrong "internal error" path (leaking the MPI op/type and `cgrfdat`) instead of the clean all-failed path at line 218. The twin `vdgraph_separate_sq.c:180-189` does this correctly (extra `MPI_Allreduce` of the flag, debug-only). Trigger: rank-asymmetric failure of the sequential strategy — rare (typically OOM), but the check is unambiguously wrong versus both its intent and its twin.

**2. `vdgraph_separate_df.c:141-144` — missing `return` on the collective memory-error path; use-after-free / NULL write.** High confidence.

```c
if (reduglbtab[0] < 0) {                        /* If memory error */
  if (ielsloctax != NULL)
    memFree (ielsloctax + grafptr->s.baseval);  /* Free group leader */
}
```

The twin `bdgraph_bipart_df.c:143-147` has `return (1)` inside this block. Here control falls through: unless the unrelated `reduglbtab[0] == 0 || reduglbtab[1] == 0` test happens to hit, all ranks continue into the initialization loop at lines 169-183 writing `ielsloctax[vertlocnum]` — a use-after-free on the ranks that just freed the array, and a write through NULL(-based) on the rank whose allocation failed. Trigger: OOM on any rank (the error is correctly made collective via the `Allreduce`; only the reaction is broken).

**3. `bdgraph_bipart_sq.c:185-201` — error flag `reduloctab[5]` is reduced but never checked, and the base adjustment is applied to a NULL pointer.** High confidence, OOM trigger.

```c
if ((dgrfptr->partgsttax = (GraphPart *) memAlloc (dgrfptr->s.vertgstnbr * sizeof (GraphPart))) == NULL) {
  errorPrint ("bdgraphBipartSq: out of memory (1)");
  reduloctab[5] = 1;                        /* Allocated data will be freed along with graph structure */
}
dgrfptr->partgsttax -= dgrfptr->s.baseval;
```

The op propagates the flag (`inout[5] |= in[5]`, line 95) but no code ever reads `reduglbtab[5]`. On allocation failure the routine proceeds and `commScatterv` (line 242) receives into `partgsttax + baseval == NULL`. The `-= baseval` outside the failure check also corrupts the struct field, so the promised "freed along with graph structure" cleanup would free an invalid pointer. (Same slot-`[5]` flag in `bdgraphBipartMlUncoarsen` *is* checked, line 356 — this is `sq`-specific.)

**4. `hdgraph_gather.c:205` — uninitialized pointer freed on the root's OOM path.** High confidence on mechanism, OOM trigger.

```c
if (chekglbval != 0) {
  if (verthaltax != NULL)
    memFree (verthaltax + dgrfptr->s.baseval);
```

`verthaltax` is a stack variable assigned only inside `if (cheklocval == 0)` (line 188). If the *root's own* allocations failed earlier (lines 146-168 set `cheklocval = 1`), that block is skipped and `verthaltax` is read uninitialized; garbage non-NULL stack content leads to `free()` of a wild pointer. Non-root ranks are safe (their `memAllocGroup` at line 189 NULLs `verthaltax` on failure — it is the first pointer of that call). Reached from every multi-sequential ordering leaf (`hdgraphOrderSq`, `hdgraphOrderNdFold2`).

**5. `hdgraph_order_nd.c:325` — leaf ordering return value discarded.** High confidence.

```c
hdgraphOrderSt (grafptr, cblkptr, paraptr->ordstratlea); /* Order this leaf */
hdgraphExit    (grafptr);                     /* Free graph at this level   */
return (0);                                   /* Leaf has been processed    */
```

When the separator strategy cannot separate further, the leaf is ordered and the routine unconditionally reports success. The separator-block call 55 lines later checks its result (`o = hdgraphOrderSt (...); ... if (o != 0) goto abort;` lines 380-384). A failed leaf ordering (OOM, strategy error) yields a silently incomplete/invalid `Dorder`, which downstream consumers trust.

**6. `hdgraph_order_nd.c:231-232` and `kdgraph_map_rb_part.c:335-336` — short-circuit `||` between two collective fold phases; rank-local failure of the first deadlocks the second.** High confidence on mechanism, OOM/rank-asymmetric trigger.

```c
o = hdgraphOrderNdFold2 (&fldthrdtab[0]) ||   /* Perform inductions in sequence */
    hdgraphOrderNdFold2 (&fldthrdtab[1]);
```

Both `Fold2` calls perform collectives over the **full** parent communicator (`hdgraphInduceList` / `dgraphInducePart` run on all processes for each part in turn). If the part-0 phase fails on one rank only, `||` skips that rank's part-1 phase while every other rank enters its collectives → hang instead of error. The threaded variant (`Fold3`) does not short-circuit and is immune.

**7. `bdgraph_bipart_ex.c:130, 245`, `bdgraph_bipart_st.c:355-362`, `vdgraph_separate_st.c:314` — `abs()` applied to `Gnum`.** High confidence that the truncation exists; practical trigger needs |imbalance| > 2^31.

```c
if ((abs (grafptr->compglbload0dlt) < compglbloaddltmax) || /* If nothing to do */
```

`Gnum` is `INT` (`dgraph.h:111`), which is 64-bit in `INTSIZE64`/`SCOTCH_Num=int64` builds; `abs()` takes `int`. `common.h` provides no 64-bit override (checked). With total loads beyond 32 bits, the exactifier's "nothing to do" test, its imbalance-reduction loop seed, and the best-partition comparisons in the two strategy selectors compute wrong absolute values. Sequential code may share the idiom; these four sites are in this territory.

**8. `bdgraph_bipart_ml.c:103-107` — default case of the fold switch guarded by the wrong (sequential) debug macro.** Certain but currently latent.

```c
#ifdef SCOTCH_DEBUG_BGRAPH2
    default :
      errorPrint ("bdgraphBipartMlCoarsen: invalid parameter");
      return (1);
#endif /* SCOTCH_DEBUG_BDGRAPH2 */
```

Opening guard says `BGRAPH2`, closing comment `BDGRAPH2`; the vdgraph twin compiles its `default:` unconditionally (`vdgraph_separate_ml.c:104-107`). Latent only because `fold` is a `STRATPARAMCASE` parameter (parser restricts `foldval` to 0-2); if that ever changes, `foldval` is used uninitialized.

**9. `vdgraph_separate_ml.c:383, 388, 390, 450` — vdgraph collective-error debug paths gated on `SCOTCH_DEBUG_BDGRAPH1`/`BDGRAPH2`.** Certain, quality-only: building with only the vdgraph debug macros does not enable these vdgraph checks.

No further findings in the files read at full depth. `hdgraph_fold.c`, `hdgraph_induce.c`, and the `check/store/zr` files were only skimmed; no claim of cleanliness for those beyond control-flow level.

## Test coverage

Essentially untested directly. In `external/scotch/src/check/`:

- **No test at all** calls `SCOTCH_dgraphMap`/`SCOTCH_dgraphPart` — the entire `bdgraph_*` and `kdgraph_*` stack (27 of the 36 files) has **zero** coverage from `src/check`; it is exercised only by the standalone `dgpart`/`dgmap` programs and by library users.
- `test_scotch_dgraph_order.c` is the single test reaching this territory, end-to-end through `SCOTCH_dgraphOrderCompute` → `hdgraph_order_nd/sq/si` → `vdgraph_separate_ml/df/sq/zr` → `hdgraph_gather/fold/induce`, with the default strategy only. It verifies return codes and gross consistency, not ordering quality, and never exercises `vdgraph_separate_bd` or non-default strategies.
- Consequently every finding above sits on a path no in-tree test can hit: findings 1-4 and 6 need rank-asymmetric failures; finding 5 needs a failing leaf strategy; finding 7 needs 64-bit loads.

## PyScotch relevance

- `Dgraph.part()` (`pyscotch/dgraph.py:975`) goes through `SCOTCH_dgraphMap` → `kdgraphMapRbPart` → the full `bdgraph_*` stack — PyScotch is now exercising 27 files that Scotch's own check suite never runs. `Dgraph.order_compute()` (`dgraph.py:1235`) exercises the `hdgraph_*`/`vdgraph_*` stack that `test_scotch_dgraph_order.c` covers only for the default strategy.
- **Determinism expectations:** results are reproducible only for a fixed rank count and a reset RNG. `bdgraphGatherAll`/`vdgraphGatherAll` intentionally desynchronize the generator per rank (2×`proclocnum` draws + frontier permutation), the OpBest reductions break ties by lowest rank, and fold-dup assigns halves by rank ranges — so partitions/orderings will legitimately differ between `-n 2` and `-n 4` runs of the same graph. Hypothesis tests should assert invariants (balance, separator validity, permutation validity), never cross-rank-count equality. PyScotch never resets the PRNG implicitly (mirroring upstream; the former `reset_random` parameters were removed) — tests wanting reproducibility must call `pyscotch.random_reset()` themselves, and consecutive `part()` calls legitimately differ without it.
- **Strategy strings reach rarely-executed code:** the exactifier (`x`/`bipart_ex`), band (`b{...}`), diffusion (`d{...}`), and multi-sequential (`q{...}`) methods, plus non-default `fold=` settings, are all reachable from user strategy strings and are exactly where findings 1-3 and 7 live. If PyScotch grows strategy-string tests for `Dgraph.part()`, prefer small comms (2-3 ranks) with balance/frontier assertions.
- **Failure mode is a hang, not an exception:** findings 1, 3, 6 and the general non-collective-OOM convention mean that under memory pressure or partial failure the MPI job deadlocks rather than returning nonzero. PyScotch cannot rely on error codes propagating out of `dgraphMapCompute`/`dgraphOrderCompute` in those situations; test harnesses need timeouts, and OOM-robustness should not be claimed for the distributed API.
