# G26-metis-dual-esmumps — summary (series based on the COMBINED series: base-combined = v7.0.17 + 142 commits of 20 groups; patches/0001..0008 apply on top of it with `git am`)

CLI-05 still-present ran medium -> 0001-Bugfix-apply-the-Fortran-null-array-convention-to-al.patch (+ 0002, objective from OBJTYPE only, Refs CLI-19/CLI-05)
CLI-15 still-present partly-run medium -> 0003-Bugfix-clean-up-properly-on-error-in-METIS_MeshToDua.patch (+ 0004 for the libscotch double free it exposed)
CLI-09 still-present partly-run medium -> 0005-Bugfix-return-the-ordering-status-from-ParMETIS_V3_N.patch
CLI-10 still-present ran high   -> 0006-Bugfix-report-failures-of-the-ordering-and-symbolic-.patch
CLI-22 still-present ran low    -> 0006 (same commit: test_esmumps tests `ncmpa != 0`, INTSTRING)
BLD-19 still-present ran low    -> 0007-Always-test-esmumpsv-in-the-esMUMPS-test-program.patch
BLD-17 still-present ran medium -> 0008-Bugfix-build-libesmumps-once-when-making-esmumps-and.patch
PS2-G26-1 (new) still-present ran medium -> 0004-Bugfix-reset-freed-vertex-array-in-graph-builders-on.patch (meshGraphDual/Nodal, graphLoad, graphGeomLoadChac)
PS2-G26-2 (new) still-present ran low -> no patch (flex yy_fatal_error exit(2) in the strategy lexer on OOM; design decision)

Three most important facts
1. All seven leads are real in 7.0.17 and in the combined series (none of these lines were touched upstream or by the 20 groups except
   G25's optionGet line in PartMeshDual); every one was run: ASan/UBSan for CLI-05/CLI-09, an LD_PRELOAD malloc injector
   (repro/tools/failmalloc.c, caller-targeted) on a non-sanitized build for CLI-10/15/22/PS2, six-run make -j loops for BLD-17.
2. The review's "MUMPS-style negative code" for CLI-10/22 is wrong: MUMPS 5.7.3 tests `IF (NCMPA .NE. 0)` (ana_orderings_wrappers_m.F:445),
   so esmumps2() keeps returning 1 and the test driver now tests `!= 0`; the driver is also linked with -lscotcherrexit in both
   build systems, which hid the defect. The first pass followed the review on this point.
3. New defect PS2-G26-1 (medium): meshGraphDual(), meshGraphNodal(), graphLoad() and graphGeomLoadChac() free the vertex array on
   the second allocation failure but leave it in a GRAPHFREETABS graph, so the caller's SCOTCH_graphExit() (or graphLoad's own
   graphFree) frees it again: "double free" / "free(): invalid pointer" through SCOTCH_graphLoad, SCOTCH_graphGeomLoadChac,
   SCOTCH_meshGraph and METIS_PartMeshDual. Hidden in the shipped tools by the exiting error library.

Tests: check_libmetis_v3/v5, check_libmetis_dual_v3/v5, check_libmetis_dual_f_v3/v5, check_libesmumps, `make escheck`,
check_libparmetis_v3 (now also with 3 processes), check_prog_dgord: all pass in the 32-bit and 64-bit ASan trees, 0 warnings;
the series re-applies with `git am` on a fresh clone after the combined series. New/extended tests: test_libmetis_dual.c
(+checkPart/checkObjval, Fortran-null and VOL cases, C and Fortran), test_libparmetis.c (+checkSizes, 3-process run in
Makefile and CMake), test_libesmumps.c (esmumpsv branch unconditional).

Could not do / decisions for the user
- CLI-15's memFree()/free() mismatch and the SCOTCH_DEBUG_ALL return, and CLI-09's "METIS_OK after a failed Compute/Perm", were
  fixed from the source (no COMMON_MEMORY_CHECK build, no MPI fault injection); everything else was run before and after.
- 0002 changes documented behaviour of METIS_PartMeshDual (vsize no longer implies the volume objective; doc updated), as G25's
  CLI-19 commit did for the graph routines. Drop 0002 if that twin change is not wanted; 0001 stands alone.
- 0004 touches G-owned loader files (graph_io.c, graph_io_chac.c from the combined series) for the same two-line pattern; 0005 adds
  a 3-process run to check_libparmetis_v3 (CMake twin added). ci/ and src/libscotchmetis/Makefile untouched (G30).
- Extra instance left to G25: metis_graph_part.c Volume path reads a Fortran-null vsize (== xadj) as sizes (wrong volume, no crash).
- PS2-G26-2 (flex exit(2) on OOM inside stratParserParse) needs a maintainer decision on how to unwind from yylex.
