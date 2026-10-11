# Graph core — Scotch v7.0.11

## Scope

Sequential graph core of `src/libscotch`: the `Graph` structure lifecycle
(`graph.c`, `graph_base.c`, `graph_clone.c`, `graph_check.c`), coarsening /
matching (`graph_coarsen.c`, `graph_coarsen_edge.c`, `graph_match.c`,
`graph_match_scan.c`), induced subgraphs (`graph_induce.c`), band / diameter
(`graph_band.c`, `graph_diam.c`), edge-load inversion (`graph_ielo.c`), file I/O
(`graph_io.c` + the `graph_io_chac.c` / `graph_io_habo.c` / `graph_io_mmkt.c` /
`graph_io_scot.c` geometry loaders), and the ordering data structures
(`order.c`, `order_check.c`, `order_io.c`, `hall_order_h[dfx].c`, `geom.c`).
The relevant C API wrappers (`library_graph.c`, `library_graph_coarsen.c`) were
read to connect internals to PyScotch's ctypes surface.

Calibration bugs (graph_color sparse-graph miscolorings; the 5 interface-layer
rename-table / contextOptionSetNum issues) are treated as known and are **not**
re-reported.

## Architecture

### The `Graph` struct and its invariants (`graph.h:134`)

Arrays are stored *based* ("tax" = table-access, offset by `-baseval`), so
`verttax[baseval] .. verttax[vertnnd-1]` are the valid vertex slots. `baseval`
is 0 or 1 (C vs Fortran style); `vertnnd == vertnbr + baseval` is an invariant
checked first thing in `graphCheck` (`graph_check.c:105`).

- **Compact vs non-compact.** A graph is *compact* when `vendtax == verttax + 1`
  — i.e. one contiguous `[vertnbr+1]` array where vertex `v`'s edges are
  `edgetax[verttax[v] .. verttax[v+1]-1]`. Non-compact graphs keep a separate
  `vendtax[]` so a vertex's edge range need not abut the next vertex's. Almost
  every routine special-cases the compact form via the literal test
  `vendtax != verttax + 1` (e.g. `graph_base.c:106`, `graph_clone.c:85,107`).
  `graphLoad` and the geometry loaders always build compact graphs;
  `graphInduce3` collapses to compact (`graph_induce.c:345`); coarsening can
  deliberately produce a non-compact graph under `GRAPHCOARSENNOCOMPACT` when
  multithreaded (`graph_coarsen.c:240,268`).

- **`edlotab`/`velotab` ownership & GRAPHFREE flags.** The flag word
  (`graph.h:81-90`) records both grouping and ownership: `GRAPHFREEEDGE`,
  `GRAPHFREEVERT`, `GRAPHFREEVNUM`, `GRAPHFREEOTHR`, plus `GRAPHVERTGROUP` /
  `GRAPHEDGEGROUP` marking that several logical arrays share one `memAllocGroup`
  block. `graphFree` (`graph.c:117-154`) frees the *group leader* (`verttax`)
  and only frees `vendtax`/`vnumtax`/`velotax`/`edlotax` separately when they
  are neither the compact alias nor part of the vertex/edge group. `graphInit`
  defaults `flagval = GRAPHFREETABS` (own everything); `SCOTCH_graphBuild`
  sets `GRAPHNONE` (own nothing — see PyScotch relevance). `graphFree` resets
  `flagval = GRAPHNONE` at the end (`graph.c:153`) so a second `graphFree` /
  `graphExit` is a documented safe no-op — the double-free guard the calibration
  patterns warn about is present here and looks correct.

- **baseval propagation.** `graphBase` (`graph_base.c`) rebases every array in
  place and adjusts the compact tail entry `verttax[vertnnd]` only in the
  compact case (`graph_base.c:106-111`). Loaders derive `baseadj = baseval -
  filebase` and add it to every edge end, *unless* vertex labels are present, in
  which case `baseadj` is forced to 0 because the relabel pass
  (`graphLoad2`) resolves ends by label instead (`graph_io.c:154-155`).

### Coarsening / matching design

`graphCoarsen` (`graph_coarsen.c:579`) → `graphCoarsen2` (sequential driver) →
`graphCoarsen3` (threaded core, run via `contextThreadLaunch`). Matching
(`graph_match.c`) fills a `finematetax[]` where mated vertices point at each
other and an unmated/self-matched vertex points at itself; the second index of
each `GraphCoarsenMulti` pair is always the larger vertex number
(`graph_coarsen.c:315,351`). Coarse vertices are created only when
`finematenum >= finevertnum`, guaranteeing each multinode is emitted once.

Matching is templated: `graph_match_scan.c` is `#include`d 8× with
Seq/Thr × edlo/no-edlo × pfix/no-pfix macro combos (`graph_match.c:88-145`),
dispatched through `graphmatchfunctab[fumaval]`. **Isolated-vertex handling**
(`graph_match_scan.c:119-149`): an edgeless vertex, if `GRAPHCOARSENNOMERGE` is
clear, is mated with any still-free vertex pulled from the *tail* of the
degree-sorted queue; if none remains it self-matches. `SCOTCH_COARSENNOMERGE`
disables that, leaving isolated vertices as singleton multinodes. The C API
masks the flag down to `GRAPHCOARSENNOMERGE` only (`library_graph_coarsen.c:104`).

Edge array construction over-allocates `finegrafptr->edgenbr * 2` Gnums
(edge + edge-load interleaved) and `memRealloc`s down to the true coarse edge
count once known (`graph_coarsen.c:254,470`). Sequential runs are always forced
compact (`graph_coarsen.c:522-524`).

### Ordering data structures

`Order` (`order.h`) is `peritab` (inverse permutation) plus a column-block tree
rooted at `rootdat` (an `OrderCblk` with `typeval`, `vnodnbr`, `cblknbr`,
`cblktab`). `orderCheck` (`order_check.c`) validates `peritab` is a bijection
via a scratch `permtab` and recursively checks the tree with `orderCheck2`,
enforcing per-type arities (NEDI 2-3 sons, DICO exactly 2, leaves 0). `orderExit`
frees the tree recursively and frees `peritab` only under `ORDERFREEPERI`
(`order.c:125`). The Halo AMD-family orderings live in `hall_order_h[dfx].c`
(hd = Halo Approximate Minimum Degree, hf = Halo Approximate Minimum Fill,
hx = shared helpers); these are dense elimination-graph codes operating on their
own `pe/iw/len` work arrays rather than on `Graph`.

## Code-quality observations

- The compact-graph test is an open-coded `vendtax != verttax + 1` scattered
  across ~a dozen sites rather than a predicate/macro; correctness depends on
  every author remembering it. No defect found, but it is fragile.
- I/O header fields (`chavertnbr`, `chaedgenbr`, `mrownbr`, `linenbr`,
  Harwell-Boeing `habcolnbr`/`habnzrnbr`) are read with `atol`/`sscanf`/`intLoad`
  and used for allocation sizing with essentially **no range validation**
  (non-negativity, overflow of `* 2`). A negative or huge declared count
  produces a negative→`size_t` allocation that only fails by luck.
- `graphBand` (`graph_band.c`) writes discovered vertices into the caller's
  `queutab` with no capacity argument or bounds check
  (`graph_band.c:153` `queutab[queunextidx ++] = vertend`). The contract that
  the caller sized `queutab` for the whole band is implicit.
- `graph_match.c:237-257` carries a large `#if 0` dead reduction routine.
- `graphInduce2`/`graphInduce3` reuse `edlotax` as scratch for the
  `orgindxtax` translation table (`graph_induce.c:261` "TRICK"), a deliberate
  but subtle aliasing that makes the code hard to audit.

## Findings

### F1 — Off-by-one heap write in Chaco loader on inconsistent edge count (medium)

`graph_io_chac.c:225`
```c
      if (edgenum > (grafptr->edgenbr + 1)) { /* Test edge array overflow */
        errorPrint ("graphGeomLoadChac: bad input (5)");
        graphFree  (grafptr);
        return     (1);
      }
      grafptr->edgetax[edgenum ++] = chavertnum;
```
`edgetax` is allocated with exactly `grafptr->edgenbr` elements and then based
(`grafptr->edgetax --`, `graph_io_chac.c:154`), so valid indices are
`1 .. edgenbr`. The guard rejects only `edgenum > edgenbr + 1`, so when
`edgenum == edgenbr + 1` the check passes and `edgetax[edgenbr + 1]` is written
— one Gnum past the end of the block. The analogous guard in the core loader
(`graph_io.c:225`, `degrval > edgennd`) is correct, which makes this a genuine
off-by-one rather than a base-1 convention.

Failure mechanism: a Chaco (`.grf`/Chaco) file whose header declares fewer edges
than the adjacency lists actually contain drives `edgenum` to `edgenbr + 1`; the
first excess arc is written out of bounds (heap corruption), and only a *second*
excess arc trips the error. Confidence medium: the index arithmetic is
unambiguous, but it requires a malformed/inconsistent input file and the loader
is a non-default path (not reachable through PyScotch's usual `graphBuild`).

### F2 — Unvalidated row index in Harwell-Boeing loader (medium/low)

`graph_io_habo.c:277-280`
```c
      habnzrtab[habnzrnum] = habnzrval;
      if (habnzrval != vertnum) {                 /* If not loop edge      */
        grafptr->verttax[vertnum] ++;             /* Account for arc       */
        grafptr->verttax[habnzrval] ++;           /* Add arc to symmetrize */
```
`habnzrval` is parsed digit-by-digit from the file (`graph_io_habo.c:267-271`)
and used directly as an index into `verttax` (here and at
`graph_io_habo.c:304` `edgetax[grafptr->verttax[vertend] ++]`) with no check
that `1 <= habnzrval <= habcolnbr`. A row index outside the declared column
range yields out-of-bounds increments/writes into the vertex and edge arrays.

Failure mechanism: malformed or truncated `.rsa` Harwell-Boeing matrix. Column
pointers *are* sanity-checked (`habcoltab[habcolnbr] == habnzrnbr + 1`,
`graph_io_habo.c:242`) but the row indices themselves are not. Confidence
medium/low: the read path is fixed-format legacy and rarely exercised, and I did
not build a PoC file.

### F3 — I/O header counts used for allocation without validation (low)

Multiple loaders (`graph_io_chac.c:131-137`, `graph_io_mmkt.c:153-168`,
`graph_io_habo.c:187-191`) compute allocation sizes such as
`chaedgenbr * 2`, `2 * linenbr`, `habnzrnbr * 2` directly from file-declared
counts with no non-negativity or multiplication-overflow guard. On a hostile
file these become negative→`size_t` (giant) or wrapped sizes. In practice
`memAlloc` returns NULL and the loaders clean up, so this is a robustness /
defense-in-depth note rather than a confirmed exploitable bug. Confidence low.

No defects were found in `graph_coarsen.c`, `graph_match*.c`, `graph_band.c`,
`graph_diam.c`, `graph_induce.c`, `graph_clone.c`, `graph_base.c`,
`graph_ielo.c`, `graph_check.c`, or the ordering files
(`order*.c`, `hall_order_h[dfx].c`) beyond the observations above — the
coarsening multinode edge cases (isolated / self-matching) and the graphFree
flag handling that the calibration flagged as fruitful all appear correct here.

## Test coverage (`src/check/test_scotch_graph_*.c`)

Present graph-core tests: `coarsen`, `color`, `diam`, `dump`, `induce`, `map`,
`map_copy`, `order`, `part_ovl` (plus `mesh_graph`). Notably **absent**:

- **All source-graph I/O loaders.** There is no `test_scotch_graph_io*`,
  `_chac`, `_habo`, or `_mmkt` test — F1 and F2 sit in completely untested code.
  The only exercise `graphLoad`/`graphSave` get is incidentally, as the input
  step of other tests.
- `graph_band.c` (`graphBand`) — no direct test; only reached via internal
  band-graph separators, whose boundary cases (`distmax == 0`, empty frontier,
  fixed-vertex `pfixtax`) are unvalidated.
- `graph_clone.c`, `graph_ielo.c`, `graph_base.c` (`SCOTCH_graphBase`), and
  `graphCheck` itself have no dedicated test.
- `graph_match.c` is tested only transitively through
  `test_scotch_graph_coarsen.c`.

`test_scotch_graph_coarsen.c` (read in full) checks only **multinode/mate-array
structural consistency** (`checkCoarMult`, `checkFineCoar`) and prints ratios —
it never calls `SCOTCH_graphCheck` on the produced coarse graph, so coarse
*edge* correctness is verified only when the library is compiled with
`SCOTCH_DEBUG_GRAPH2` (which triggers the internal `graphCheck` at
`graph_coarsen.c:559`). This matches the CLAUDE.md caution that "C test passes"
≠ "output correct"; PyScotch property tests should assert `graphCheck` on
coarsened output explicitly.

## PyScotch relevance

- **`SCOTCH_graphBuild` keeps your pointers; it does not copy** (`library_graph.c:249-260`).
  It sets `flagval = GRAPHNONE` and stores `verttax = (Gnum*)verttab - baseval`,
  `edgetax = (Gnum*)edgetab - baseval`, and likewise for `vendtab`, `velotab`,
  `vlbltab`, `edlotab`. Consequences for the ctypes layer passing numpy arrays:
  - The numpy arrays **must outlive the `SCOTCH_Graph`** and must not be
    reallocated/garbage-collected while any Scotch call can touch the graph.
    Hold references (the wrapper must keep the numpy objects alive for the graph's
    lifetime); a temporary array passed inline is a use-after-free.
  - Because `flagval` is `GRAPHNONE`, `SCOTCH_graphExit`/`graphFree` will
    **not** free these arrays — correct for borrowed numpy buffers, but it means
    a graph *built* this way and a graph *loaded* by Scotch have opposite
    ownership; never `graphExit` a loaded graph's arrays yourself and never
    assume a built graph frees them.
  - Aliasing is detected by pointer identity only: `vendtab == verttab`,
    `velotab == verttab`, `edlotab == edgetab` collapse to the compact/no-array
    case. Passing the *same* numpy array object for two roles is silently
    interpreted as "absent". Passing two numpy arrays that happen to be distinct
    objects but describe compact adjacency requires `vendtab = NULL` (or `==
    verttab`) to get the compact representation Scotch's fast paths expect.

- **dtype / width.** `Gnum` is `INT` (`graph.h:102`), whose width follows the
  build (`-DINTSIZE64` etc.). numpy arrays must match (`int32` vs `int64`) or the
  based-pointer arithmetic reads garbage. Use `SCOTCH_numSizeof()` — do not assume.

- **baseval pitfalls.** `SCOTCH_graphBuild` only warns (does not reject) a
  `baseval` outside {0,1} and only under `SCOTCH_DEBUG_LIBRARY1`
  (`library_graph.c:244`). Every edge end in `edgetab` must already be expressed
  in the chosen base; there is no relabeling on `graphBuild` (unlike `graphLoad`,
  which rebases/relabels). A 0-based numpy adjacency handed to a graph declared
  `baseval=1` produces silent out-of-range edge ends.

- **`graphCheck`'s actual guarantees** (`graph_check.c:87-207`, exposed as
  `SCOTCH_graphCheck`). It verifies: `vertnbr`/`vertnnd` consistency; `edgenbr`
  non-negative and even; per-vertex `verttax[v] >= baseval` and
  `vendtax[v] >= verttax[v]`; every edge end in `[baseval, vertnnd)`; **no
  self-loops**; **symmetry** (every arc has a matching reverse arc with equal
  edge load); **no duplicate arcs**; and that `edgenbr`, `velosum`, `edlosum`,
  `degrmax` match recomputed values (with load-sum overflow checks). It does
  **not** validate `vnumtax`/`vlbltax`, and — critically — **`SCOTCH_graphBuild`
  never calls it.** A malformed numpy adjacency is accepted silently at build
  time and only surfaces as corruption/crash inside a later algorithm. PyScotch
  should call `SCOTCH_graphCheck` after every build in debug/test paths; it is
  the only line of defense, and its symmetry + no-duplicate + no-loop guarantees
  are exactly the invariants numpy-constructed CSR graphs most often violate.
