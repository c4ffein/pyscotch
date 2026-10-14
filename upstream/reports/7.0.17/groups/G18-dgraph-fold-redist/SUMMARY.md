# G18-dgraph-fold-redist: summary (second pass, redone from the dead attempt's claims)

DGR-01   still-present  ran        high    -> patches/0002, 0003 (fold: baseval first; collective gate before edge data, unconditional first agreement, one cleanup path; hdgraphFold2 twin)
DGR-02   still-present  ran        high    -> patches/0002
DGR-22   still-present  partly-run low     -> patches/0003 (Waitall checked), 0007 (int-count checks in dgraphFoldComm, fold receivers, dgraphRedist2 totals)
PS-DGR-4 still-present  ran        medium  -> patches/0003, 0004, 0006 (fold, gather, redist agreements always performed)
DGR-04   still-present  ran        high    -> patches/0001 (+ regression case in src/check/test_scotch_dgraph_redist.c)
DGR-14   fixed-in-7.0.17 ran       low     -> -
DGR-10   still-present  ran        medium  -> patches/0004 (dgraphGatherAll2 reworked like hdgraphGather; hdgraphGather's own uninitialised fields fixed)
API-04   fixed-in-7.0.17 ran       high    -> -
PS2-G18-2 (extra) dgraphFoldComm debug double free -> patches/0005; PS2-G18-1 (hdgraph_induce.c unchecked memRealloc) and PS2-G18-3 (hdgraphOrderNd2 halves disagree): other groups' files, alt diff / notes only.

Series: 7 commits on v7.0.17, `git am` clean on a fresh clone, stylecheck adds nothing (removes 4 pre-existing items), `git diff --check` clean,
0 warnings on 32-bit ASan, 64-bit and -DSCOTCH_DEBUG_ALL trees; all 14 CHECKPTSCOTCH targets pass on 32-bit and 64-bit; 6 dgraph targets pass on the debug tree.

Three most important facts
1. Every out-of-memory inside dgraphFold2/hdgraphFold2 (receiver or sender, 7 allocation points each), dgraphRedist (4 points) and dgraphGatherAll2
   (3 points) hangs or crashes the whole job on pristine 7.0.17 release builds (LD_PRELOAD fault injection, repro/common); after the series every one
   returns 1 on every rank. The receiver edge-array case (DGR-01) needed a new collective gate because the senders' edge Isends can never be matched.
2. DGR-04 is a silent wrong result through the public API as documented (permgsttab in any order): rc=0 and a graph that fails SCOTCH_dgraphCheck.
   The existing test could not see it (receivers' own send buffers pad the gap); the added case (everything to the last process, reversed) fails
   on pristine with an ASan memcpy overlap or "invalid redistributed graph (2)" and passes patched.
3. The dead attempt's design was sound and mostly kept, but it left DGR-22's redist int totals unpatched (they overflow before Alltoallv is ever
   reached) and its redist-collective commit kept the comma-chain structure; both are now done in the maintainer's goto idiom (hdgraphGather 0635547).

Could not do / residual
- DGR-22's overflow itself (16 GB per message) is not runnable; the checks are no-ops here. MPI-call failures remain unrecoverable (fatal by default), as before.
- Redist fault injection still hangs at one point inside dgraphHaloSync2 (dgraph_halo.c, another group); ordering still disagrees between folded halves
  (hdgraph_order_nd.c) and crashes on an unchecked memRealloc in hdgraph_induce.c: all recorded in extra.json with diffs where I could write them.
- The debug-only agreements of dgraphFold2 after the gate (fail5/fail6) were kept: nothing but MPI calls can fail there (dgraphBuild4 does not allocate).

User decisions
- Unconditional MPI_Allreduce agreements in release builds (one to three small collectives per fold/gather/redist) reverse the maintainer's explicit
  "cannot be merged with a useful one" choice; the alternative piggyback idiom (his 3c9b3ab) exists only for dgraphRedist's first agreement (alt/PS2-G18-1-B...).
- Whether to also make the two post-gate fold agreements unconditional (one more Allreduce; not needed for allocation failures).
