# G08-bgraph-gg-gain — summary

SEP-06    fixed-in-7.0.17   ran   high    -> - (2d94960; reverting it: cut 47 vs 35 on m16x16, single thread)
SEP-11    still-present     ran   medium  -> patches/0001 (ABS in the cross-thread reduction)
SEP-13    still-present     ran   high    -> patches/0002 (spawn in launcher) + patches/0003 (deterministic option, graphMatch idiom)
SEP-19    fixed-in-7.0.17   ran   low     -> - (2a6fd07; injected fault: graphPart returns 1 with fix, 0 without)
SEP-20    fixed-in-7.0.17   ran   low     -> - (f545452 + 813ef60; tree grep clean; 64-bit build + 6 check targets pass)
PS-SEP-3  still-present     ran   low     -> patches/0004 (per-table dummy link in GainTabl, fibo.h rootdat idiom)
PS2-G08-1 still-present     ran   high    -> patches/0003 (option ignored: passes shared over all threads)
PS2-G08-2 still-present     ran   medium  -> - (kgraph_map_rb_part.c:316 splits the context with a 2nd random stream
                                              regardless of the option; 1 thread != >=2 threads; maintainer decision)

Three facts that matter
1. After 0001-0004, SCOTCH_DETERMINISTIC=1 gives one partition in 30 fresh processes at 1, 2, 4 and 8 threads,
   2 == 4 == 8, on 32- and 64-bit builds; TSan reports nothing with the option set and, without it, only the
   intentional lock-free matching (graph_match_scan.c). Pristine: 3 distinct at 2 threads, 19-26 TSan reports/run.
2. PyScotch's shipped patch is behaviourally right but not in the maintainer's idiom: the NULL-descriptor collapse is
   replaced by graphMatch's "non-zero threads return at once" with a working-thread count in BgraphBipartGgData;
   contdat/contptr and thread 0's use of the caller's context must stay (1-thread result unchanged: 1d497d7d).
3. The gain sentinel race also crosses split sub-contexts (FM in one, GG in the other) and goes through the gain.h
   gainTablDel macro, which rules out the conditional-write and thread-local alternatives; the per-table link is the
   only option that keeps the TRICK and the macro. Compiling gain.c with -DSCOTCH_DEBUG_GAIN3 was necessary: the
   debug checkers needed the table pointer (caught a missed call site).

Not done / needs the user
- No regression test added: a "1 thread == N threads with the option set" test (natural home test_scotch_context.c)
  fails on pristine+series because of PS2-G08-2, outside this group (kgraph_map_rb / common_context). The user must
  decide whether to send PS2-G08-2 as a design question ("do not split when deterministic" vs document ">= 2 threads").
- Two libc abs() on SCOTCH_Num remain in src/check tests (test_arch_deco.c:192, test_scotch_arch_build.c:354); not
  patched (test code, tiny values, no ABS macro available there) — info only.
- The pre-existing UBSan "non-zero offset to null pointer" reports in kgraph_map_ml.c:239 / bgraph_bipart_ml.c:195
  appear in every check run (pristine too); they belong to the ML groups.

Verification: 32-bit and 64-bit builds 0 warnings; check_common_random, check_common_thread, check_scotch_context,
check_scotch_graph_map, check_prog_gpart, check_prog_gmap pass on both, plus a -DSCOTCH_DEBUG_ALL -DSCOTCH_DEBUG_GAIN3
build; stylecheck.py and git diff --check clean; series re-applied with git am on a fresh clone (trees identical).
