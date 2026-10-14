# G15-order-io-seq-misc — summary (Scotch 7.0.17)

GRA-03   still-present ran high   -> patches/0001 (orderLoad: count must equal vnodnbr, rank range + duplicate check via peritab marker; test_scotch_graph_order gets a save/load round trip + 4 invalid files)
CLI-23   still-present ran low    -> patches/0002 (esMUMPS orderLoad: cblknbr >= 0, range array partition check, rank range/duplicates; orderSave keeps status, no read of empty permtab)
PS-BLD-1 still-present ran low    -> patches/0009 (SCOTCH_graphOrderCheck checks permtab against peritab; s_l.tex updated; precedent esmumps/order_check.c)
GRA-25   still-present ran low    -> patches/0003 (orderExit on error in hgraphOrderCp AND hmeshOrderCp) + 0004 (PS2-G15-1, see below)
GRA-22   still-present ran medium -> patches/0007 (strategy run once; column loads in ordering order; static Bl2 splits tree leaves; mesh twin recursion fixed)
GRA-14   still-present ran medium -> patches/0008 (graphCoarsen2 acts on retuval: free mating array / partial coarse graph, return 2; thread-side hash/lock/mating leaks fixed)
GRA-27   still-present ran info   -> patches/0005 (delotab -> edlotab; generated code of a graph with edge loads now compiles)
PS2-G08-2 (forwarded) still-present ran medium -> patches/0006 (hgraph_order_nd.c + hmesh_order_nd.c: no context split when deterministic; same idiom/wording as G12's 0009; gord 30x at 1/2/4 threads: 30/30 differing before, 0/30 after)
PS2-G15-1 (extra) still-present ran medium -> patches/0004 (hgraphOrderCc: init all tree cells before ordering; pristine SCOTCH_graphOrderExit after failed 'o{strat=b{cmin=0}}' = invalid free)
PS2-G15-2/3 (extra) still-present ran -> patches/0007 (b{strat=n{...}} never terminated; trailing zero-load columns left out of all blocks)
PS2-G15-4..8 (extra) alt/ or notes only: unchecked shrinking memRealloc (tree-wide), .ord line-order doc mismatch, gotst ignores load status (G27), missing Fortran scotchfgraphorderload (docs), hgraphOrderNd error-path leaks (inconclusive).

Three most important facts
1. The two ordering-file loaders are now exact twins of G14's graphLoad discipline: the .ord mutation fuzz (1500 mutants, seed 42) went from 248 sanitizer hits
   (intLoad OOB write, orderPeri OOB write/SEGV) to 78, all UBSan parse overflow inside intLoad() (common_integer.c, G07); no memory-safety hit remains.
2. GRA-22 is bigger than reported: besides the vertex-order weight sum (blocks 24..16930 for cmin=1200 -> 954..1577 now), 'b' re-ran its strategy on every sub-block
   (hang for b{strat=n{...}}) and dropped trailing zero-load columns (inconsistent tree). The review's "Fix:" (go back through peritab) is the code a90b1cb removed
   because it is out of bounds on induced subgraphs; the committed fix builds the loads in ordering order (sort-matching of original indices for subgraphs).
3. GRA-14: with an LD_PRELOAD allocation injector every failing allocation point of graphCoarsen/graphCoarsenMatch (1 and 4 threads) now returns 2 with LSan clean;
   pristine returned 0 with a freed graph (use-after-free), an unfilled graph, or an invalid mating array. One contract (retuval) replaces three ad-hoc tests.

Verification: 9 commits on v7.0.17, git am clean on a fresh clone; 32-bit and 64-bit ASan+UBSan trees build with 0 warnings; check_scotch_graph_order/dump/coarsen/map/induce,
check_scotch_mesh_graph, check_prog_gord, check_prog_gord_block, check_prog_gotst, check_prog_mord, check_prog_gpart, check_libesmumps rc=0 on both trees (logs/; the
first 64-bit run of gord/gotst failed only because both trees shared $(TMPDIR)=/tmp concurrently, rerun alone: rc=0). Pre-existing sanitizer lines only
(bgraph_bipart_ml.c:195, kgraph_map_ml.c:239, mesh_induce_sepa.c:160). stylecheck.py reports only pre-existing lines; git diff --check clean.

Could not do / for the user or maintainer to decide
- check_prog_gcv does not exist in src/check/Makefile (gcv is not exercised by any check target); check_scotch_graph_order_f does not exist either.
- No src/check test for CLI-23 (esMUMPS orderLoad is only reachable from the unbuilt test_fax), GRA-25 (needs LSan + failing strategy), GRA-14 (needs an injector);
  repro/*/README give the exact commands. GRA-22 is covered by the existing check_prog_gord (ole=b on a weighted graph) and check_prog_gord_block.
- PS2-G15-4 (shrinking memRealloc unchecked, 8 sites tree-wide) and PS2-G15-5 (manual says .ord lines may be in any order, loader requires vertex order) are
  decisions for the maintainer; PS2-G15-6 (gotst) is G27's file, PS2-G15-7 (Fortran wrapper) is docs/API: alt diffs provided, nothing committed outside this group.
- G10 (hmesh_order_nd.c SEP-15) had no patches when 0006 was committed; the hunk is minimal (declaration + split condition) so both series should apply.
- 0009 touches library_graph_order.c, which G05's 0003/0006 also touch (different regions).
