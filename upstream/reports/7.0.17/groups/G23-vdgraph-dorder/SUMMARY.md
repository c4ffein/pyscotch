# G23-vdgraph-dorder: second-pass summary (series based on the combined series, tag base-combined)

DMO-05  still-present ran        medium -> patches/0001 (free on the all-invalid path; Vdgraph debug flags = G22's DMO-18 ml sibling)
DMO-12  still-present ran        low    -> patches/0003 (VdgraphStore saves/restores complocload; vdgraphCheck compares local loads)
PS-DMO-1 not-a-bug    ran        info   -> resolved by 0003 (the z shortcut mirrors vgraphSeparateZr and is right once the store is complete)
DMO-04  still-present ran        medium -> patches/0004 (5th summed slot = allocation flag, tested first, return on all processes)
DMO-14  still-present source-read low   -> patches/0007 (return (-1); manual already says "negative value")
DMO-15  still-present ran        low    -> patches/0008 (+0010 at the source: kdgraphMapRbPartSequ mapAlloc+kgraphFrst, G24's file)
DMO-02  still-present ran        high   -> patches/0005 (+ based labeled graph in check_prog_dgord / CMake)
DMO-13  still-present ran        low    -> patches/0006
DMO-11  vdgraph half (bdgraph half is G22's 0005): still-present partly-run low -> patches/0002, same design (ABS at the producers)
DMO-18  vdgraph half (bdgraph half is G22's 0006): still-present ran low -> patches/0001 (ml debug flags) + patches/0011 (sq partial-failure check)
DMO-09: n/a to vdgraph (no `bal` strategy variable).
Extras: PS2-G23-1 dmapSave null-pointer offset (0009); PS2-G23-2 NULL fragment part array at the source (0010); PS2-G23-3 vdgraphCheck
messages/leak (messages fixed in 0003); PS2-G23-4 unchecked shrink realloc (G24 file, note); PS2-G23-5 timing-dependent hang of a
folded sub-communicator after a collective band failure (inconclusive, pristine and patched alike); PS2-G23-6 Df halo-sync failures
return alone (PS-DGR-2 family, G20's decision).

Series: 11 commits on base-combined (v7.0.17 + 142 combined commits); `git am` clean on a fresh clone (trees identical); stylecheck
adds nothing over the pre-existing items; `git diff --check` clean; 0 warnings on 32-bit ASan, 64-bit and DEBUG_ALL trees.
check_scotch_dgraph_order, check_prog_dgord, check_prog_dgpart, check_scotch_dgraph_check, check_prog_dgscat-dggath run at np 1-4 on
32- and 64-bit: identical PASS/FAIL pattern to base-combined (the only FAILs are data/small1-%r.grf, which needs 4 processes, and
`dgscat -r1` at np=1); whole `ptcheck` PASS on 32-bit (patched and pristine) and 64-bit; the 3 sanitizer notes are the pre-existing
library_dgraph_coarsen.c:163 (G21). Every reproducer fails on base-combined and passes patched (repro/<ID>/README, repro/common/).

Three most important facts
1. DMO-02 is memory corruption plus a silently wrong `dgord` output for every based, labeled graph: glibc itself aborts on a
   chunk-aligned 14-vertex graph (both dorderSave and the tree writer); fixed as the exact twin of the maintainer's 4290e22, with
   the NULL guard that 4290e22 lacks (UBSan reports the non-root null offset in dmapSave: 0009).
2. The forwarded dmapSave NULL-part-array lead is really a producer bug (kdgraphMapRbPartSequ, any user `r{...}` without seq=) that
   also crashes SCOTCH_dgraphMap in dmapTerm before dmapSave is reached; G20's per-loop guard HANGS at np=3 (a non-root process breaks
   out of its sends). 0008 validates collectively in the initial reduction (empty-or-complete count as dmapTerm, no fragment without
   part array); 0010 fixes the source like graphMapCompute2's 8e06be2.
3. DMO-04: injected failure on one rank -> null-pointer store (SEGV) on pristine; with 0004 all processes return 1 and the ML low
   strategy takes over. G22's DMO-04 half (its 0003, bdgraphBipartDf) must keep the same layout: 5 slots, [4] = summed allocation
   flag tested first after the Allreduce, basing in the else branch, free + return; alt/DMO-04-twin-... is that diff.

Could not do / caveats
- The first pass's drv.c and my first driver called MPI_Init, not MPI_Init_thread(MPI_THREAD_MULTIPLE): fold-dup coarsening then hangs
  at random. All results were redone with the fixed driver; first-pass "hang" readings for DMO-04 are unreliable for that reason.
- PS2-G23-5 could not be isolated (no gdb; 1 run in 3; needs the fold/halo owners). PS2-G23-6 is G20's open halo decision.
- DMO-14's error path (MPI failure) and DMO-15's dead test are shown by source and by an internal-API driver, not through a user tool.
- Orderings change with the series (DMO-11 tie-breaks, DMO-12 restored loads): e.g. 802 -> 818 column blocks for 4elt at np=2.

User decisions
- Keep 0010 (kdgraph_map_rb_part.c, owned by G24; hunks 240 lines apart from DMO-16's) or route it to G24; 0008 stands alone either way.
- 0004 and G22's bdgraphBipartDf commit should be squashed or kept textually identical; 0001/0002/0011 are the vdgraph halves of G22's 0006/0005.
- DMO-15's committed test rejects partial mappings (dmapTerm's rule); the review's weaker range test is alt/DMO-15-B.
