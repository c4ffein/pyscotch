# Separators & halo ordering — Scotch v7.0.11

## Scope

Reviewed at submodule tag `v7.0.11` (`/home/dev/workspace/pyscotch/external/scotch`), directory `src/libscotch/`:

- **Vertex separators (14 files)**: `vgraph.c/.h`, `vgraph_check.c`, `vgraph_store.c`, `vgraph_separate_{bd,df,es,fm,gg,gp,ml,st,th,vw,zr}.c`
- **Halo graphs + ordering (16 files)**: `hgraph.c/.h`, `hgraph_check.c`, `hgraph_dump.c`, `hgraph_induce.c`, `hgraph_induce_edge.c`, `hgraph_order_{bl,cc,cp,gp,hd,hf,hx,kp,nd,si,st}.c`

Depth: **deep-read** `vgraph_separate_fm.c` (all 937 lines, including the gain/balance arithmetic and the resize path), `hgraph_order_nd.c` (all 317 lines), `hgraph_order_bl.c`, `hgraph_order_cc.c`, `hgraph_order_hd/hf.c`, `hgraph_induce_edge.c`, `vgraph_separate_gg.c`, `vgraph_separate_gp.c`, `vgraph_separate_bd.c`, `vgraph_separate_ml.c`, `hgraph_order_gp.c`, `hgraph_order_kp.c`, `hgraph_order_si.c`, plus `vgraph_check.c`/`hgraph_check.c`. **Skimmed only**: `vgraph_separate_es.c` (König-cover machinery not line-verified), `hgraph_order_cp.c` (compression, 900+ lines), `hgraph_dump.c`, `hgraph_order_st.c`/`vgraph_separate_st.c` (method-table wiring checked). Two findings were **reproduced empirically** against the project's 7.0.12-based build in `scotch-builds/lib64` (code identical in v7.0.11 sources for the paths involved).

## Architecture

### Vgraph: the 3-part model

`Vgraph` (vgraph.h:74) is a graph plus `parttax` with values {0, 1, 2}, where 2 = separator. Invariants (enforced by `vgraphCheck`, vgraph_check.c:80):

- `compload[3]`: loads of part 0, part 1, separator; sums to `s.velosum`.
- `compsize[2]` only — **separator size is not stored redundantly**; it is `fronnbr`, and `frontab[0..fronnbr)` must list exactly the vertices with `parttax == 2`.
- `comploaddlt == compload[0]*dwgttab[1] - compload[1]*dwgttab[0]` (weighted-target balance; `dwgttab` are subdomain weights, both 1 under nested dissection — hgraph_order_nd.c:158).
- Separation property: a vertex in part p has no neighbor in part 1-p (vgraph_check.c:162). Note `vgraphCheck` only *warns* about useless separator vertices (no neighbor in one part) and only under `SCOTCH_DEBUG_VGRAPH3`.

### Separator FM (`vgraph_separate_fm.c`)

Vertex-FM à la Ashcraft-Liu: only separator vertices sit in the gain table, each with **two** gain links (`gainlink0`/`gainlink1` = move-to-part-0 / move-to-part-1). A pointer trick distinguishes them: `veloval` is stored **negated**, so a fetched link whose `veloval >= 0` is actually `gainlink1` and the code rewinds by the intra-struct offset (fm.c:121–126). `compgain[p] = -velo(v) + load(neighbors in part 1-p)` — moving v to p pulls its cross-neighbors into the separator. The balance-delta formula used both in candidate selection (fm.c:132) and in the commit (fm.c:401) is `(1-2p)·(gain·dwgt[p] + velo·(dwgt[0]+dwgt[1]))`; I verified the two are algebraically consistent with the `comploaddlt` invariant and with the final reconstruction `compload[0] = (dlt + (velosum - c2)·dwg0)/(dwg0+dwg1)` (fm.c:674, exact integer division). Rollback uses a `savetab` journal keyed by `mswpnum` epochs; hash-table resize (`vgraphSeparateFmResize`) temporarily translates saved hash slots to vertex numbers and back (fm.c:743, 806–815). Frontier and `compsize` are rebuilt at the end from the hash table only — correct because every vertex that was ever in the separator is in the hash table. The isolated-separator-vertex shortcut (`gaincur == veloval`, fm.c:129) deliberately bypasses the balance test; the main loop then ratchets `comploaddltmax` up (fm.c:622) and back down (fm.c:624–637). This bookkeeping is intricate but I found no drift; the `SCOTCH_DEBUG_VGRAPH3` checker (fm.c:831) recomputes all three loads and both gains per vertex.

### Hgraph halo semantics

`Hgraph` (hgraph.h:71) = graph where vertices `[baseval, vnohnnd)` are non-halo (to be ordered by this subproblem) and `[vnohnnd, vertnnd)` are halo (owned by enclosing separators, ordered elsewhere). Per non-halo vertex the edge sub-array is split: non-halo edges in `[verttax[v], vnhdtax[v])`, halo edges in `[vnhdtax[v], vendtax[v])`. `hgraphInduceList`/`hgraph_induce_edge.c` builds induced subgraphs preserving this: neighbors of selected vertices that are unselected become new halo vertices; halo–halo edges are dropped (halo vertices keep only edges back into the non-halo part, hgraph_induce_edge.c:189–196). `vnlosum`/`enohnbr`/`enlosum` track non-halo totals. All ordering methods iterate only to `vnohnnd` and traverse only to `vnhdtax` (verified in si, cc, gp, kp), so halo vertices are never assigned an inverse-permutation slot by a sub-block.

### Nested dissection (`hgraph_order_nd.c`)

`hgraphOrderNd` strips the halo (`hgraphUnhalo`, hgraph.c:122 — shallow aliasing, free-flags cleared), separates with `vgraphSeparateSt`, and terminates recursion when either part is empty (nd.c:175) — the leaf strategy `ordstratlea` is then applied to the *halo* graph. Since each recursion strictly reduces the non-halo vertex count (both parts non-empty), termination is structural; no pathological non-termination found. Parts 0/1 recurse via `hgraphOrderNd2` (possibly context-split across threads), separator is induced **without** halo (`graphInduceList`, nd.c:256 — a deliberate design: the separator gets the highest indices in its range and its halo is dropped) and ordered by `ordstratsep`. Ordering offsets: part 0 at `ordenum`, part 1 at `+size0`, separator at `+size0+size1` (nd.c:270, 292–297). `cblktab` gets 3 children (NEDI node), or 2 when the separator is empty; `ordeptr->cblknbr/treenbr` updates are mutex-protected.

### hd/hf bridges to hall_order AMD

`hgraphOrderHd/Hf` (hd.c:88–178, hf.c:88–182) flatten the halo graph via `hgraphOrderHxFill` into MUMPS-style `pe/len/iw` arrays, run `hallOrderHdR2Halmd` (halo approximate minimum degree) resp. `hallOrderHfR3Hamdf4` (halo AMD with fill metric), then `hallOrderHxBuild` amalgamates supervariables into a column-block tree, writing the inverse permutation directly at `ordeptr->peritab + ordenum`. `norig = s.velosum` (vertex loads = amalgamated column counts from graph compression); the apparent hd/hf divergence in `secntab` sizing (`norig+1` vs `n`) is **not** a bug — the same local name maps to Halmd's `head [norig]` vs Hamdf4's `wf [n]`, and Hamdf4 gets its own `headtab [nbbuck+2]`. Both fall back to `hgraphOrderSi` when `vnlosum < colmin`.

## Code-quality observations

- **Dead methods, still compiled**: `vgraphSeparateDf` (diffusion, 12 KB) and `vgraphSeparateTh` (separator thinner, vgraph_separate_th.c:74) have **no callers** — neither appears in the strategy method table (vgraph_separate_st.c:121–129: only b,e,f,h,g,m,v,z) nor in any other `.c` file, yet both are in the Makefile/CMake build. Same for v6.1.0, so this is longstanding. Risk: they receive no testing at all; if ever re-wired, they are effectively unreviewed.
- `vgraph_separate_vw.c` is a debug method (dumps `vgraphseparatevw_output_%08d.map`) using a file-scope static counter — not thread-safe under context-split ND, harmless otherwise.
- Error paths in `vgraphSeparateFm` leak on OOM: fm.c:588–591 returns 1 without `memFree(hashtab)`/`gainTablExit(tablptr)` after a failed resize (and the many `SCOTCH_DEBUG_VGRAPH2` early returns likewise). Cosmetic in practice — callers abort the strategy.
- Off-by-one asymmetry in FM acceptance: entry test treats `abs(dlt) <= comploaddltmat` as balanced (fm.c:196) but move recording requires strictly `comploadabsdlt < comploaddltmat` (fm.c:596), so a solution *exactly at* the tolerance is only recorded if the incumbent is out of bounds. Conservative, not corrupting.
- Twin divergence (cosmetic): the pseudo-diameter loop runs `passnum <= paraptr->passnbr` in `hgraph_order_gp.c:137` but `passnum < paraptr->passnbr` in `vgraph_separate_gp.c:131` — the separator variant does one fewer BFS pass than the ordering variant for the same `pass` parameter.
- `hgraph_order_bl.c` history is instructive: upstream commit `a90b1cb` (post-7.0.10, in 7.0.11) fixed an out-of-bounds access (`velotax[peritab[vnodnum]]` indexed subgraph-local `velotax` with *original-graph* numbers) by switching to plain index order — see finding 3.

## Findings

### 1. `hgraphOrderBl` — unbounded self-recursion → stack-overflow crash when the sub-strategy produces a partitioned tree (REPRODUCED, high confidence)

`hgraph_order_bl.c:96–97` (entry) and 192–199 (recursion):

```c
  if (hgraphOrderSt (grafptr, ordeptr, ordenum, cblkptr, paraptr->straptr) != 0) /* Perform ordering strategy */
    return (1);
  ...
  else {                                          /* Block already partitioned */
    for (cblknum = 0; cblknum < cblkptr->cblknbr; cblknum ++) {
      if (hgraphOrderBl (grafptr, ordeptr, ordenum, cblkptr->cblktab + cblknum, paraptr) != 0)
```

Mechanism: when the sub-strategy (e.g. `f` = halo-AMD, whose `hallOrderHxBuild` routinely emits a multi-block SEQU tree) leaves `cblkptr->cblktab != NULL`, `hgraphOrderBl` recurses into each child — but the recursive call **unconditionally re-runs the whole sub-strategy on the full graph** at the same `ordenum`, attaching a fresh multi-block tree under the child, which again triggers the recursion. Depth grows without bound; additionally every level rewrites `peritab[ordenum..]` for the entire graph. Reproduced: 12×12 grid, strategy `b{cmin=2,strat=f{cmin=2,cmax=5,frat=0.0}}` → SIGSEGV; backtrace shows a long chain of `hgraphOrderBl → hgraphOrderBl → … → hgraphOrderHf → hallOrderHxBuild` frames until stack exhaustion. Controls `f{…}` alone and `b{cmin=2,strat=s}` both succeed with a valid permutation. Same structure exists in v6.1.0, so it has never worked for tree-producing sub-strategies. The default strategies never compose `b` this way, which is why it goes unnoticed; but the strategy string is a documented public interface. (The single-block split path also assumes the block spans the whole graph — `SCOTCH_DEBUG_HGRAPH2` even asserts `cblkptr->vnodnbr == grafptr->vnohnbr` at bl.c:100 — so a leaf child with fewer vertices additionally gets a nonsensical split from whole-graph `vnlosum`.)

### 2. `hgraphOrderCc` DICO nodes with ≥3 components fail `SCOTCH_graphOrderCheck` (REPRODUCED, high confidence; producer/checker contradiction)

`hgraph_order_cc.c:206–207`:

```c
  cblkptr->typeval = ORDERCBLKDICO;               /* Node becomes a set of disconnected components */
  cblkptr->cblknbr = rootnbr;
```

vs. the checker, `order_check.c` (`orderCheck2`):

```c
        ((cblkptr->typeval == ORDERCBLKDICO) &&
         ((cblkptr->cblknbr != 2)))) {
      errorPrint ("orderCheck2: invalid number of column blocks (1)");
```

Mechanism: the connected-components method (`o`, and the `SCOTCH_STRATDISCONNECTED` predefined strategy which wraps everything in `o{strat=…}`, library_graph_order.c:517) creates one child per component, but `orderCheck2` hardcodes DICO arity 2. Reproduced: 3 disconnected triangles, strategy `o{strat=s}` — `SCOTCH_graphOrderCompute` returns 0 with a valid permutation and `cblknbr=3`, then `SCOTCH_graphOrderCheck` on the *same* ordering fails with `orderCheck2: invalid number of column blocks (1)`. One of the two sides is wrong (order_check.c is outside my territory; the distributed `dorderDico` chains components as nested binary nodes, which is probably what the checker was written for). Consequence: any caller that validates orderings with `graphOrderCheck` gets a spurious failure on 3+-component graphs ordered with the officially recommended disconnected-graph strategy.

### 3. `hgraphOrderBl` weighted split walks vertices in index order, not permutation order (medium confidence, quality bug)

`hgraph_order_bl.c:163–166`:

```c
        do {                                      /* Accumulate weights until bound is reached */
          vnlosum += grafptr->s.velotax[vnodnum];
          vnodnum ++;
        } while (vnlosum < vnlomax);
```

The block boundaries are meant to cut the *ordered* sequence of columns into ~`cblkmin`-load chunks (block k covers permuted positions `[vnodbas, vnodnum)`), but the loads are accumulated over vertex indices `baseval..`, i.e. in graph order. Whenever the leaf permutation produced by the sub-strategy is not the identity (e.g. `b{strat=g}` after compression, where `velotax` holds amalgamated column counts), block k's declared `vnodnbr` is derived from the loads of the *wrong* vertices, so the resulting blocks do not have the intended balanced loads. Upstream commit `a90b1cb` ("do not get vertex loads through inverse permutation") replaced a genuinely out-of-bounds access (`velotax[peritab[vnodnum]]`, with `peritab` holding original-top-graph numbers) with this index-order walk — trading a crash for an approximation without a comment saying so. The correct weight of position i is `velotax` of the subgraph-local preimage, which would need an inverse of `vnumtax`. Total block count and `Σ vnodnbr = vnohnbr` remain consistent (the loop is bounded by `vnlosum < grafptr->vnlosum` and every block takes ≥1 vertex), so orderings stay *valid* — only the block-size objective is silently off.

### No further findings

Specifically checked and found sound: FM's 3-way `compload`/`compsize` bookkeeping including the superscalar `compsize1add/sub` frontier rebuild (fm.c:652–680); FM resize's reverse-order save-array move over the overlapping realloc region and two-segment rehash (fm.c:739–800); GG's part-encoding-in-pointer states and end-of-pass load reconstruction (gg.c:279–297); ML uncoarsening's `compsize` reconstruction from `finesize1` and frontier expansion of multinodes (ml.c:155–190, checked against `vgraphCheck` invariants); BD's anchor-vertex loads, the "at least one missing vertex per part" size guard that makes the recycled `qtab` frontier fit, and the anchor-part fallback (bd.c:210–216, 373–420); ND's list-building pointer arithmetic over `frontab` (nd.c:182–192); induce's non-halo/halo edge split and `enohnbr` accumulation (hgraph_induce_edge.c:92–146); kp's empty-part compaction (kp.c:145–160); hd/hf array sizing against the hall_order formal parameters.

## Test coverage

- `src/check/test_scotch_graph_order.c` is the **only** sequential ordering test: it orders one graph with the **default strategy only** (plus a repeat to test order reuse) and runs `SCOTCH_graphOrderCheck`. The default strategy exercises `n` (nd), `m`+`f`+`b(bnd)` vgraph separation (ml, vertex-FM, bd), `f` (hf) leaves and `g` (gp) separator ordering — via one graph.
- `test_strat_seq.c` only *parses* the predefined strategy variants (including `SCOTCH_STRATDISCONNECTED`); it never computes an ordering, which is exactly why finding 2 survives.
- **No direct test at any strategy setting** for: `vgraph_separate_{bd,es,gg,gp,th,df,zr,vw}` as user-selected methods, `hgraph_order_{bl,cc,cp,kp,hd,si}` (hd not even in the default graph strategy — only hf is), and none of the vgraph methods have a unit test of the Vgraph invariants (that safety net exists only when compiled with `SCOTCH_DEBUG_VGRAPH2/3`, which release builds are not).
- `hgraphCheck` (hgraph_check.c:75) does not verify `enohnbr` against `Σ(vnhdtax[v]-verttax[v])` (for unweighted graphs `enlosum` is *initialized from* `enohnbr`, hgraph_check.c:97, so the comparison at :113 is a tautology), nor `vnlosum` against the actual non-halo load sum. An induce bug corrupting these totals would pass the debug checker and only surface as bad hd/hf decisions (`vnlosum < colmin` cutoffs, `norig`).

## PyScotch relevance

- **`SCOTCH_graphOrderCheck` is weaker than it looks.** It verifies: `peritab` is a bijection, tree node types/arities, and that children's `vnodnbr` sum to the parent's (plus global `cblknbr`/`treenbr` consistency). It does **not** verify the separator property (that an NEDI node's third block actually separates the first two), nor anything about `rangtab`/`treetab` (those are emitted by the library layer from the internal tree, not re-checked), nor block-load balance (finding 3 is invisible to it). Hypothesis tests that want to validate orderings should re-derive: `rangtab[0] == baseval`, `rangtab` strictly increasing, `rangtab[cblknbr] == baseval + vertnbr`, `treetab` parent indices in `[-1, cblknbr)` and topologically consistent, and — the strong one Scotch never checks — for each ND node, no edge between the two child vertex sets.
- **Do not treat `graphOrderCheck` failure as proof of a bad ordering** on disconnected graphs: per finding 2, a perfectly valid ordering computed with `SCOTCH_STRATDISCONNECTED` / `o{…}` on a 3+-component graph fails the check. If PyScotch exposes `stratGraphOrderBuild` flags, this combination deserves an explicit test and possibly a documented caveat (`QUESTIONS_FOR_SCOTCH_TEAM.md` material).
- **Guard user-supplied strategy strings**: `b{strat=X}` where X can produce a partitioned tree (`f`, `d`, `n`, `o`, `c`, `k`) crashes the process by stack overflow (finding 1) — from Python this is an uncatchable hard crash of the interpreter. Worth a note wherever PyScotch lets strategies through verbatim.
- Return-code conventions here match the project's CLAUDE.md notes: separator/ordering methods return 0/1 only (1 = error, strategy aborted); there is no "not possible" 1-vs-2 distinction in this layer, and several OOM paths return 1 after leaking method-local memory — irrelevant for correctness, but repeated failure-path calls from a long-lived process won't reclaim it.
- The `comploaddlt`/`dwgttab` machinery only matters to PyScotch indirectly (nd always uses weights 1:1); the observable contract is the `cblktab` tree flattened to `rangtab`/`treetab`, with the ND child order fixed as [part0, part1, separator] and the separator occupying the *highest* index range of its subtree — a property worth asserting in tests since consumers (e.g. MUMPS-style solvers) rely on it.
