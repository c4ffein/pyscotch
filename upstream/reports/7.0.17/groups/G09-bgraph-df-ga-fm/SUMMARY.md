# G09-bgraph-df-ga-fm — summary (patches/0001..0009 on v7.0.17; git am verified on a fresh clone)

SEP-05    fixed-in-7.0.17  ran        high    -> - (f37f70d complete; 7.0.16 interposer gives another partition, 1 == 4 == 8 threads on 7.0.17)
SEP-14    still-present    ran        medium  -> patches/0009 (barrier after allocation, error returned, overflow stamped per thread by pass number)
SEP-04    still-present    ran        high    -> patches/0002 (guard < 3 + new check_prog_gpart/CMake gpart_5 line on p2-p2.grf)
SEP-12    still-present    ran        medium  -> patches/0006 (barrier + intRandSpawn contexts, G08 idiom) + patches/0007 (deterministic option)
SEP-09    still-present    ran        medium  -> patches/0001 (return (1) after the clean-up, as kgraphMapFm())
SEP-10    still-present    ran        medium  -> patches/0005 (free-vertex loads only in bgraphZero/bgraphSwal; convention documented in bgraph.h)
PS-SEP-5  still-present    partly-run low     -> patches/0005
GRA-26    still-present    ran        info    -> patches/0004 (ternary NULL guard at the two sites, library_graph_map.c:260 idiom)
PS2-G09-1 still-present    ran        medium  -> patches/0003 (GA pop=0: heap write before the deme array)
PS2-G09-2 still-present    ran        medium  -> patches/0008 (GA champion never replaces an imbalanced start: 'a' alone was a no-op)
PS2-G09-3 still-present    ran        medium  -> patches/0007 (GA ignores the deterministic option)
PS2-G09-4 still-present    source-read medium -> - (kgraph_map_df.c, group G13: abort `goto fail` skips two barriers; per-pass flag race; alt diff given)
PS2-G09-5 still-present    ran        medium  -> patches/0009 (DF abort flag set by a fast thread read by slow threads: reproduced hang)

Three facts that matter
1. SEP-14 is worse than described and the first pass's fix is incomplete: the overflowing thread skips the anchor reduction
   (for-loop increment), a desynchronised thread returns into threadWaitBarrier() and re-runs the loop on the launcher's dead
   stack (ASan stack-use-after-return, reproduced with malloc injection and with NaN injection), and a slow thread can observe
   a fast thread's overflow flag at the post-allocation test and leave early: a reproduced HANG (nan_C_trace.log). Patch 0009
   keeps the shared flag for errors only (written before barriers) and stamps overflows with the pass number per thread.
   kgraph_map_df.c has the same two design flaws (PS2-G09-4, G13's file).
2. The genetic method was unusable on its own: with the champion compared against an unpenalized current cost, 'a' from a
   zero partition leaves every vertex in part 0 (PS2-G09-2); plus SIGFPE on 2-vertex jobs (SEP-04), heap write with pop=0
   (PS2-G09-1), 32-37 TSan races per run (SEP-12, 0 after the series), and thread-count-dependent results unless the
   deterministic option is honoured (PS2-G09-3; with it, 1 == 2 == 4 == 8 threads on 32- and 64-bit).
3. SEP-10 is a real debug-build failure for users: any fixed-vertex mapping whose strategy applies 'z' after a non-zero
   partition fails with "bgraphCheck: invalid part load" under SCOTCH_DEBUG_BGRAPH2; release builds hide it because GG/FM/DF
   recompute the loads. The convention (loads and sizes exclude fixed vertices; checker already enforces it) is now documented.

Verification: 32-bit and 64-bit ASan+UBSan builds and a -DSCOTCH_DEBUG_ALL build with 0 warnings; check_scotch_graph_map,
check_prog_gpart (incl. the new line), check_prog_gmap, check_scotch_graph_order, check_scotch_context, check_scotch_graph_part_ovl,
check_prog_gpart_overlap, check_prog_gpart_remap, check_scotch_graph_coarsen pass on 32/64-bit with 0 sanitizer reports (debug build:
graph_map, gpart, gmap, context); stylecheck.py reports only pre-existing lines; git diff --check clean; no UBSan null-offset report left.
Not done / needs the user
- PS2-G09-4 (kgraph_map_df.c) is G13's file: alt diff compiled, not run; G13 should port the pass-stamp idiom of patch 0009.
- Patch 0007 (GA deterministic option) mirrors G08's patch 0003 / graphMatch(); separate commit, droppable if the maintainer disagrees.
- No regression test for SEP-14/SEP-09 (fault injection) nor SEP-10 (debug-only, needs a fixed-vertex input the tools do not take);
  a determinism test is blocked by PS2-G08-2 (kgraph_map_rb_part.c splits the random stream regardless of the option).
