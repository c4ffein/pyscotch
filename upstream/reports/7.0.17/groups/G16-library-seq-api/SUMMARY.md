# G16-library-seq-api -- summary (Scotch 7.0.17)

| id | status | method | sev | patch |
|---|---|---|---|---|
| API-03 | fixed-in-7.0.17 (d604eb1, complete: Raw/Remap/Fortran share graphMapView2) | ran | high | - |
| API-14 | still-present | ran | low | patches/0001 |
| API-16 | still-present | ran | low | patches/0002 |
| PS-API-1 | still-present | ran | medium | patches/0002 |
| API-19 | still-present | ran | low | patches/0004 (+0005 cleanup) |
| API-21 | still-present | ran | low | patches/0006 |
| API-18 | still-present | ran | low | patches/0007 (+0008 labels) |
| PS-API-7 | not-a-bug (cmlosum==0 implies cdstmax==-1, loop never runs) | ran | info | - |
| PS2-G03-2 (fwd) | not-a-bug in 7.0.17 (no reachable negative distance) | partly-run | info | - (alt/ only) |
| PS2-G16-1 (new) | still-present: one unmapped vertex zeroes Processors/Target/Neighbors/PartDiam | ran | low | patches/0003 |
| PS2-G16-2 (new) | still-present: DgraphStatData.edlosum reduced but never set | source-read | info | patches/0005 |
| PS2-G16-3 (new) | distributed view labels differ (Cmlosum, missing space) | ran | info | patches/0008 |

Series: 9 commits on v7.0.17 (0009 adds src/check/test_scotch_graph_map_view + Makefile/CMake entries;
fails on pristine, passes patched, bases 0 and 1). git am on a fresh clone OK; 32- and 64-bit ASan
builds with zero warnings; stylecheck and `git diff --check` clean (two pre-existing stylecheck lines
at library_graph_map_view.c:746-747 are in the untouched SCOTCH_graphPartOvlView). Passing after the
series, 32- and 64-bit: check_scotch_graph_map, _map_copy, _map_view, check_prog_gmap, gtst, gpart,
gpart_remap, gpart_overlap, gpart_clustering, check_prog_dgtst, check_prog_dgpart, check_scotch_dgraph_check.

Three most important facts
1. gmap -v vs dgmap -v differential (same graph, same mapping, repro/API-18/dview.c): pristine differs
   on CommDelta for weighted graphs (0.657106 vs 0.406780 on m4x4_b1_ev/k4) and on two labels; after
   0007+0008 the two views are identical line for line (np 1/2/3, weighted and unweighted, base 100000).
2. Printed numbers that change for the shipped check data (SCOTCH_PTHREAD_NUMBER=1; with threads the
   mappings themselves vary run to run): every PartDiam drops by one per chained component (bump/h3
   45/55/49.75 -> 44/54/48.75; bump k9 42/54 -> 41/53; small1/m11x13 1 -> 0); bump_b100000 PartDiam
   0/0/0 -> 41/61/47.33; gpart_remap AvgMigrDist 0.000000 -> 1.000000; gtst/dgtst "Edge load sum" on
   weighted m4x4_b1_ev/elv 118 -> 59 (unweighted graphs unchanged). check_prog_gtst/dgtst still pass.
3. API-19 convention chosen: per edge (doc "sum of all edge loads", manual's arc/edge vocabulary, gtst's
   own "Edge nbr = edgenbr/2"); weighted sums halve, unweighted unchanged; doc clarified in s_l/p_l.tex.
   The first pass (and PyScotch's hypothesis-test comment) leaned the other way; alt/API-19-b has it.

Could not do / caveats
- No check test for API-19 (no unit-weighted shipped data) and API-21 (needs duplicate graph labels).
- ASan cannot fire on API-21 with the stock library (same memAllocGroup block); proven with a split-
  allocation build of the pristine routine (repro/API-21/split).
- API-09 (Dgraphstat Fortran symbol case, G17) and the `dist` loader null-pointer crash (G01) were seen
  but not touched. API-22 (graphPartOvlView, same file) belongs to G12 and is untouched.

User must decide
- API-19 convention A (edge, shipped) vs B (arc, alt/); PyScotch tests pin the current inconsistency
  (test_interop.py, test_graph*.py, hypothesis test_graph_properties.py:351-356) and must change either way.
- Whether to keep 0008 (output label change "Cmlosum" -> "CommLoad", space in "Processors").
