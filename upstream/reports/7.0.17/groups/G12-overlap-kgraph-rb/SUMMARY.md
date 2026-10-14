# G12-overlap-kgraph-rb — summary (Scotch 7.0.17)

SEP-01  still-present  ran  high   -> patches/0007 (wgraph_part_rb.c; + check line test_scotch_graph_part_ovl 3 ... 'r{sep=z}')
SEP-17  still-present  ran  low    -> patches/0008 (wgraph_part_rb.c: post-pass wgraphPartRbFron)
API-22  still-present  ran  low    -> patches/0001 (library_graph_map_view.c)
GRA-01  still-present  ran  high   -> patches/0003 (kgraph_map_rb.c/.h; + test case in test_scotch_graph_map.c)
GRA-21  still-present  ran  low    -> patches/0004 (kgraph_map_rb.c)
GRA-23  still-present  ran  medium -> patches/0005 (mapping.c, kgraph_map_rb.c)
GRA-05  still-present  ran  high   -> patches/0002 (kgraph_band.c; + check_prog_gpart_remap lines, Makefile + CMake)
PS2-G12-1 (extra) kgraphMapRb() computes cost after failed recursion  medium -> patches/0006
PS2-G12-2 (extra) strategy without initial mapping method: NULL parttax medium -> alt diff only (library_graph_map.c, other group)
PS2-G12-3 (extra, from G08/SEP-13) deterministic option ignored by RB context split medium -> patches/0009
PS2-G12-4 (extra) int shift in hash sizing, info -> no patch

Three most important facts
1. The one-token SEP-01 fix (recurse on fake part 1) is NOT enough: when the surviving part owns a single domain the
   recursion bipartitions the graph with dwgttab {0,1} and maps vertices onto the sibling's domain (shown with r{sep=(z|f)});
   the patch maps the whole graph onto the terminal domain instead.
2. SEP-17 is broader than "isolated vertices": any separator vertex without a neighbour in a part is lost (path of 4
   vertices / 4 parts, default strategy, loses 2 vertices); the first pass's degree-zero post-pass does not fix it.
3. With patches 0009 + G08's bgraphBipartGg series, gpart results are identical for 1, 2 and 4 threads under
   SCOTCH_DETERMINISTIC=1 (0 differing lines); without 0009 they differ at every thread count (the split recurses).

Verification: all 9 commits build with zero warnings on 32-bit and 64-bit Gnum ASan trees and a SCOTCH_DEBUG_ALL tree;
check_scotch_graph_map, check_scotch_graph_map_copy, check_scotch_graph_part_ovl, check_prog_gpart, check_prog_gpart_overlap,
check_prog_gpart_remap, check_prog_gmap pass on 32/64-bit (the UBSan "offset to null pointer" lines in bgraph_bipart_ml.c:195
and kgraph_map_ml.c:239 are pre-existing, base-100000 graphs, other groups' files). Series re-applies with git am on a fresh clone.

Could not do / to decide
- GRA-05's regression test detects the bug only when uninitialised memory is non-zero (deterministic under ASan/valgrind).
- SEP-17: which part a lost vertex should join (lightest part chosen; locality-aware choice is a design decision).
- GRA-23 is a behaviour change: remapping from an old mapping with terminals outside the architecture (e.g. 32 old parts
  onto 16) is now rejected ("mapBuild3: invalid terminal array") instead of computing on uninitialised domains.
- No regression test for PS2-G12-3 in src/check (env-var driven tests have no precedent there, and it needs G08's fix too).
- PS2-G12-2 fix is in library_graph_map.c (not this group's file): alt/PS2-G12-2-a tested in a scratch tree only.
