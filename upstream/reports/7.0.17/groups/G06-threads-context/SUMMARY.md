# G06-threads-context — summary (Scotch 7.0.17)

COR-09   still-present    ran  medium -> patches/0002 (main joins the start-up barrier with the reduced count, then exits; desctab freed, lock destroyed; TSan clean)
COR-10   still-present    ran  medium -> patches/0001 (0 = "as many threads as cores", precedent test_common_thread.c:191; Import1 rejects < 1; test case added)
COR-11   still-present    ran  medium -> patches/0003 (threadProcessStateSave in Import1, mirrors Init; affinity check added to test_scotch_context.c)
COR-24   still-present    ran  low    -> patches/0004 (coretab = logical core numbers mapped through the mask, -1 kept unbound; matches s_l.tex:8179)
API-02   partially-fixed  ran  medium -> patches/0005 (Fortran scotchfcontextoptionparse + manual entry + OPTIONNUMRANDOMFIXEDSEED name); rest = PS2-G06-1
PS2-G08-2 (extra) still-present ran medium -> alt/PS2-G08-2-b (hgraph_order_nd.c, hmesh_order_nd.c guards, to extend G12's 0009); alt a (common_context.c) tested, not recommended
PS2-G06-1 (extra) still-present ran medium -> alt/PS2-G06-1-a only (design decision)
PS2-G06-2 (extra) still-present ran low    -> patches/0005
PS2-G06-3 (extra) info, source-read; PS2-G06-4 (extra) low, ran -> alt/PS2-G06-1-a

Three facts that matter
1. The run-time fixed-seed option has no consumer: CONTEXTOPTIONNUMRANDOMFIXEDSEED is stored (env, API, -C) but never read;
   intRandInit() seeds from time(NULL) unless COMMON_RANDOM_FIXED_SEED is compiled in. In a build without that flag,
   `gpart -Cd`, `-Cf`, SCOTCH_DETERMINISTIC=1 and SCOTCH_RANDOM_FIXED_SEED=1 all give different results from run to run
   (repro/PS2-G06-1). 0f793bf fixed the switch, not the symptom the review named. alt/PS2-G06-1-a fixes all three ways
   (tested) but reseeds at every context init: the maintainer must choose the semantics (once per process vs per context).
2. PS2-G08-2 verdict: the fix belongs at the callers, not in common_context.c. No common_*.c includes context.h (the option
   numbering is libscotch's; every consumer is an algorithm: graph_match.c:57,205), and a common-layer guard would also
   serialize dgraphFoldDup()'s split, which uses no random numbers. G12's 0009 is in the right place but incomplete:
   hgraph_order_nd.c:305 / hmesh_order_nd.c:261 split the same way and gord differs 1 vs 2 vs 4 threads under
   SCOTCH_DETERMINISTIC=1 (3532 / 6186 lines on bump.grf); alt/PS2-G08-2-b (same hunks as 0009) makes gord 1 == 2 == 4.
   Recommendation: 0009 + alt b (either/or with alt a, not both). Those two files belong to the ordering groups.
3. COR-24's documented semantics are "logical indices, modulus-reduced" (s_l.tex:8179-8191); the first pass's preferred
   option (physical ids) contradicts them, and its option-B sketch would have pinned a documented -1 to core 0.
   Under `taskset -c 4-7`, pristine binds coretab {4,5,6,7} (and {0,1,2,3}) to CPUs 0-3, outside the process mask.

Verification: 32/64-bit ASan trees 0 warnings; check_common_random/thread, check_scotch_context, check_scotch_graph_map at
SCOTCH_PTHREAD_NUMBER 1/2/4 x SCOTCH_DETERMINISTIC 0/1, both trees: 48/48 rc=0 (graph_map's 4 UBSan lines = pre-existing
bgraph_bipart_ml.c:195 / kgraph_map_ml.c:239); TSan tree 0 warnings (FAIL_AT=1,2,3 spawn, import, both thread checks); all
reproducers pass on both trees (repro/*/README); stylecheck/diff --check clean; git am on a fresh clone, trees identical. Logs: logs/.

Could not do / to decide
- PS2-G06-1 (seed option ineffective) and PS2-G06-4 (env SCOTCH_DETERMINISTIC does not imply the fixed seed; 'd,r' order) are
  not committed: the maintainer must pick the run-time seed semantics. PyScotch is affected only in builds without
  COMMON_RANDOM_FIXED_SEED.
- PS2-G08-2: the two ordering-side guards must go into the G12/ordering series (files outside this group); alt b is ready.
- No src/check test for COR-09 (LD_PRELOAD fault injection) nor COR-24 (restricted mask + /proc); -C missing from man pages, not patched.
- COR-10: 0 now means "automatic" (README/INSTALL still only mention -1); the user may prefer the reject variant (alt/COR-10-b).
