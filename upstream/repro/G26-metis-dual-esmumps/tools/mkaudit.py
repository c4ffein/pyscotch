import json, os
W = "/tmp/claude-1000/-home-dev-workspace-pyscotch/087f3d41-a5d8-4b0a-9260-769d70cf8179/scratchpad/work/G26-metis-dual-esmumps"
P = lambda n: f"{W}/patches/{n}"
A = lambda n: f"{W}/alt/{n}"
p1 = P("0001-Bugfix-apply-the-Fortran-null-array-convention-to-al.patch")
p2 = P("0002-Select-the-partitioning-objective-of-METIS_PartMeshD.patch")
p3 = P("0003-Bugfix-clean-up-properly-on-error-in-METIS_MeshToDua.patch")
p4 = P("0004-Bugfix-reset-freed-vertex-array-in-graph-builders-on.patch")
p5 = P("0005-Bugfix-return-the-ordering-status-from-ParMETIS_V3_N.patch")
p6 = P("0006-Bugfix-report-failures-of-the-ordering-and-symbolic-.patch")
p7 = P("0007-Always-test-esmumpsv-in-the-esMUMPS-test-program.patch")
p8 = P("0008-Bugfix-build-libesmumps-once-when-making-esmumps-and.patch")
CHECKS = ("Regression runs with the full series (base-combined + 0001..0008), 32-bit and 64-bit ASan+UBSan trees: "
          "check_libmetis_v3, check_libmetis_v5, check_libmetis_dual_v3, check_libmetis_dual_v5, check_libmetis_dual_f_v3, "
          "check_libmetis_dual_f_v5, check_libesmumps, `make escheck`, check_libparmetis_v3 (now also with 3 processes), "
          "check_prog_dgord: all pass, 0 compiler warnings (logs $WORK/build*.check_*.log, $WORK/build*.escheck.log, $WORK/build*.full.log).")

items = []

items.append(dict(
 id="CLI-05",
 our_title="PartMeshDual passes Fortran-null vwgt to graphBuild, rebases NULL vsize, ignores graphBuild status",
 status="still-present", method="ran",
 ran=("ASan build of base-combined (= 7.0.17 + 20 groups, libscotchmetis untouched for these lines), $WORK/repro/CLI-05/pm_firstpass.c:\n"
      "  ./pm 2  (vwgt == &ne, base 1) -> ==ERROR: AddressSanitizer: stack-buffer-overflow ... READ of size 4 ... #0 SCOTCH_graphBuild library_graph.c:262 #1 SCOTCH_METIS_PartMeshDual metis_graph_part_dual.c:209\n"
      "  ./pm 0  (OBJTYPE=VOL, vsize=NULL, base 1) -> metis_graph_part_dual.c:222:11: runtime error: applying non-zero offset 18446744073709551612 to null pointer; metis_graph_part.c:172:24: ... produced null pointer (SEGV in _SCOTCH_METIS_OutputVol)\n"
      "  same against pristine $INFRA/asan (7.0.17): stack-buffer-overflow at metis_graph_part_dual.c:206.\n"
      "Patched: modes 0..3 -> ret=1 objval=20/20/10/10, no sanitizer report. The patched src/check/test_libmetis_dual.c against the pristine library: base 0 -> stack-buffer-overflow, base 1 -> UBSan null-pointer offset + crash; against the patched library: passes. " + CHECKS),
 read_only="", why_not_run="",
 severity="medium",
 severity_note="Public METIS API argument; a Fortran caller passing the documented-by-code 'ne' null array crashes (stack over-read), a C caller asking METIS_OBJTYPE_VOL without vsize and base 1 crashes; same as the review.",
 location_7_0_17="src/libscotchmetis/metis_graph_part_dual.c:206 (graphBuild with raw vwgt, status dropped), :217-219 (vsize - baseval with vsize == NULL), :107-109 (only options/tpwgts/vsize get the '!= ne' treatment)",
 evidence=("7.0.17 :206 `SCOTCH_graphBuild (&graftmp, baseval, vertnbr, verttab, vendtab, vwgt, NULL, edgenbr, edgetab, edlotab);`\n"
           "7.0.17 :217-219 `if (((vsize != NULL) && (vsize != ne)) || ... (options[METIS_OPTION_OBJTYPE] == METIS_OBJTYPE_VOL))) o = _SCOTCH_METIS_OutputVol (baseval, ..., vsize - baseval, *nparts, ...);`\n"
           "7.0.17 :109 `if ((options != NULL) && (options != ne)) /* For the Fortran interface, null arrays are those equal to ne */`"),
 upstream_change="",
 review_accuracy="Accurate on all three points. Its 'Fix:' line works as written, but 'normalise vsize equal to ne to NULL' alone would still return a communication volume for the default objective whenever vsize is given (inconsistent with G25's CLI-19 fix of the graph routines), hence the second commit.",
 first_pass_critique=("Status, method and evidence correct. Its preferred diff introduces two new pointers but keeps a duplicated 9-line cleanup block for the graphBuild failure (the file's twin `_SCOTCH_METIS_PartGraph2()` nests the map inside `if (SCOTCH_graphBuild (...) == 0)` instead), keeps the raw `options[METIS_OPTION_OBJTYPE]` read (misses the -1 default handled by G25's `_SCOTCH_METIS_optionGet()`), adds no test, and leaves the vsize-implies-volume selection that G25 removed from the graph routines. Its option 2 (shared helper) is the alt diff CLI-05-b."),
 extra_instances=[
  dict(location="src/libscotchmetis/metis_graph_part.c:423-463 (_SCOTCH_METIS_PartGraph_Volume) and :598 (V5 wrappers use `options == xadj` as the Fortran null)",
       quote="vsiztax  = vsize - baseval;  /* vsize == xadj from a Fortran caller is used as a size array */",
       covered_by_patch=False),
 ],
 fix_options=[
  dict(label="Normalise the null arrays once at the top, check graphBuild by nesting the mapping (chosen)",
       summary="Local `velotab`/`vsiztab` computed once with the file's `!= ne` convention; `SCOTCH_graphBuild()` guards the strat/map block as in `_SCOTCH_METIS_PartGraph2()`; NULL vsiztab passed as NULL to `_SCOTCH_METIS_OutputVol()`; OBJTYPE read through `_SCOTCH_METIS_optionGet()`; C and Fortran tests gain the null-array call and the VOL-without-vsize call.",
       diff_file=p1, tested="pm modes 0..3, patched test_libmetis_dual (C, both bases; Fortran) in 32/64-bit ASan trees; the new test crashes on the pristine library.",
       tradeoffs="No ABI change; one more local per array. Does not touch the V5 graph wrappers (G25's file, different null reference).",
       preferred=True,
       maintainer_fit="Same shape as his own `_SCOTCH_METIS_PartGraph2()` (metis_graph_part.c:313-337: `o = 1; if (SCOTCH_graphBuild (...) == 0) { ... }`) and G25's optionGet helper; he adds the case to the existing test like 261f1c7 'Add tests for libparmetis'."),
  dict(label="Shared `_SCOTCH_METIS_arrayGet()` helper in metis_options.c",
       summary="Add a helper next to `_SCOTCH_METIS_optionGet()` returning NULL when the array equals the Fortran null reference, use it for vwgt/vsize; same graphBuild/OutputVol hunks.",
       diff_file=A("CLI-05-b-shared-array-helper.diff"), tested="untested: compile-level only (same hunks as the chosen option plus a trivial helper); not built because it changes a shared header owned by G25's series.",
       tradeoffs="One more exported internal symbol for a 1-line ternary; only pays off if the V5 graph wrappers adopt it too (they use xadj as the null reference).",
       preferred=False, maintainer_fit="He added `_SCOTCH_METIS_optionGet()` for a value that needed -1 handling; a pointer compare does not warrant a routine."),
  dict(label="First pass: inline guards at the three sites",
       summary="The first pass's diff: vwgtptr/vsizptr locals, explicit cleanup block on graphBuild failure, raw options[OBJTYPE] read.",
       diff_file=A("CLI-05-c-firstpass-inline-guards.diff"), tested="untested here (the first pass reported ASan clean on it); it was written against 7.0.17 and no longer applies on G25's optionGet lines.",
       tradeoffs="Duplicates the 6-call cleanup sequence a third time in the routine; misses the -1 default for OBJTYPE.",
       preferred=False, maintainer_fit="He avoids duplicated cleanup (goto/nesting idiom, see dgraphInduce2 in 7.0.17)."),
 ],
 patch_files=[p1, p2],
 cleanup_done="The `else o = METIS_ERROR;` branch and the second strat init/exit pair are gone (nesting); nothing else became unused. 0002 removes the unconditional vsize-implies-volume branch.",
 test_added="src/check/test_libmetis_dual.c: checkPart() factored, calls with vwgt=vsize=&ne (Fortran null), with OBJTYPE=VOL and vsize=NULL, with vsize and VOL; checkObjval() verifies objval against the dual graph of the same ncommon for cut and volume. src/check/test_libmetis_dual_f.f90.in: second call passing ne (as array element netab(1), the only form gfortran accepts next to the array call) for vwgt and vsize, with the same checks.",
 docs_updated="doc/src/scotch/s_l.tex (METIS_PartMeshDual: NUMBERING and OBJTYPE supported, vsize used for the communication volume) in 0002",
 needs="", needs_note="",
 notes=("0002 is the PartMeshDual twin of G25's CLI-19 commit 53c5f79 (objective from OBJTYPE only, vsize ignored for the edge cut): without it, a caller passing vsize with the default objective gets a volume while the graph routines now return a cut. Behaviour change documented in s_l.tex. "
        "The extra instance in metis_graph_part.c (V5 Volume path with a Fortran-null vsize == xadj) is G25's file; vwgt == xadj is harmless there because SCOTCH_graphBuild() treats velotab == verttab as NULL, but vsize == xadj is read as sizes (wrong volume, no crash). Left for G25/the maintainer, listed here."),
))

items.append(dict(
 id="CLI-15",
 our_title="Dual-graph builders: MeshToDual leaves freed xadj in caller, Mesh2Dual mismatched free and debug leak",
 status="still-present", method="partly-run",
 ran=("Plain (non-sanitized) build of base-combined, LD_PRELOAD fault injector $WORK/repro/tools/failmalloc.so, driver $WORK/repro/CLI-15/m2d_fail.c (test_libmetis_dual.c's mesh, caller tests xadj == NULL as the test and the Fortran interface do):\n"
      "  FAILMALLOC_FUNC=SCOTCH_METIS_MeshToDual FAILMALLOC_NTH=2 ./m2d_fail -> ERROR: SCOTCH_METIS_MeshToDual: out of memory / free(): double free detected in tcache 2 (abort)\n"
      "  (FAILMALLOC_AT sweep N=1..8: N=7 is this case; N=1..6 return -4 with xadj=(nil))\n"
      "  patched: METIS_MeshToDual returned -3; xadj=(nil) adjncy=(nil) / caller: error detected through xadj == NULL\n"
      "Distributed twin $WORK/repro/CLI-15/pm2d_fail.c, mpirun -np 2 -x FAILMALLOC_FUNC=SCOTCH_ParMETIS_V3_Mesh2Dual -x FAILMALLOC_NTH=1|2: base -> returned -3, xadj=0x1 adjncy=0x1 (outputs untouched); patched -> xadj=(nil) adjncy=(nil). " + CHECKS),
 read_only="The memFree()/free() mismatch (visible only with COMMON_MEMORY_TRACE/CHECK) and the SCOTCH_DEBUG_ALL early return (needs MPI_Allreduce to fail) were read, not run.",
 why_not_run="A COMMON_MEMORY_CHECK build and an MPI fault were not set up; the double free and the NULL outputs were run.",
 severity="medium",
 severity_note="Raised from the review's low: on OOM the C test program and any Fortran caller (no return value) double-free and read a freed array; the ParMETIS parts stay low.",
 location_7_0_17="src/libscotchmetis/metis_graph_dual.c:112-118 (dangling *xadj), :97-108 (no meshExit/graphExit on build failure); src/libscotchmetis/parmetis_dgraph_dual.c:150-173 (malloc/memFree), :158-162 (DEBUG_ALL return without cleanup), no NULL outputs on error",
 evidence=("metis_graph_dual.c:115-118 `if (*xadj != NULL) free (*xadj); SCOTCH_graphExit (&grafdat); return (METIS_ERROR_MEMORY);` after `*xadj = NULL; /* Assume something will go wrong */` at :92 (so callers rely on the NULL test);\n"
           "parmetis_dgraph_dual.c:150 `vertloctab = malloc (...) /* Use plain malloc() because of user-managed array */` vs :167-170 `memFree (edgeloctab); ... memFree (vertloctab);`; :159-162 `if (MPI_Allreduce (...) != MPI_SUCCESS) { ...; return (METIS_ERROR); }`"),
 upstream_change="",
 review_accuracy="Mostly accurate; wrong on one detail: METIS_MeshToDual does call SCOTCH_graphExit() in its OOM branch (:117). Its fix line is right; it misses that the distributed twin never sets its output pointers on error although its METIS v3 Fortran stub has no return value either.",
 first_pass_critique="Correct status and the graphExit correction; method 'source-read' although an LD_PRELOAD injector settles it in minutes; its sketch keeps the malloc on a line with `sizeof(SCOTCH_Num)` (missing space) and does not NULL the outputs of the distributed twin nor free the mesh on a failed meshBuildElem.",
 extra_instances=[
  dict(location="src/libscotchmetis/parmetis_dgraph_dual.c:178-179 (outputs set only on success, never NULL on error; Fortran v3 stub parmetis_dgraph_dual_f.c:92-107 has no return value)", quote="*vertlocptr = vertloctab; *edgelocptr = edgeloctab;", covered_by_patch=True),
  dict(location="src/libscotchmetis/metis_graph_dual.c:98-102 (SCOTCH_meshBuildElem failure returns without SCOTCH_meshExit; in SCOTCH_DEBUG_LIBRARY1 builds its checks (6)/(7) fail after allocation, library_mesh.c:440-453)", quote="SCOTCH_errorPrint (\"SCOTCH_METIS_MeshToDual: cannot create mesh\"); return (METIS_ERROR);", covered_by_patch=True),
  dict(location="src/libscotch/mesh_graph.c:261-266 (meshGraphDual frees verttax on OOM but leaves it in a GRAPHFREETABS graph: the graphExit that METIS_PartMeshDual performs double-frees)", quote="if (grafptr->verttax != NULL) memFree (grafptr->verttax); return (1);", covered_by_patch=True),
 ],
 fix_options=[
  dict(label="NULL outputs on entry in both routines, free() for malloc(), common exit for the debug path (chosen)",
       summary="Sequential: `*xadj = *adjncy = NULL` on entry, meshExit/graphExit on every failure, `*xadj = NULL` after the free. Distributed: outputs NULL on entry, free() instead of memFree(), communication error sets chekglbval and goes through the existing abort labels, status METIS_ERROR_MEMORY only when the local allocation failed.",
       diff_file=p3, tested="m2d_fail / pm2d_fail before and after; check_libmetis_dual_* and check_libparmetis_v3 in both trees.",
       tradeoffs="None visible to callers that already test the return value; Fortran callers now get NULL on all failures.",
       preferred=True, maintainer_fit="Mirrors the sequential routine's own `/* Assume something will go wrong */` idiom and the file's `/* Use plain malloc() because of user-managed array */` comment; abort labels already exist in the distributed routine."),
  dict(label="Allocate into locals and publish the outputs only on success",
       summary="MeshToDual keeps `xadjtab`/`adjntab` locals and assigns `*xadj`/`*adjncy` after the copies; nothing to reset after a free.",
       diff_file=A("CLI-15-b-local-arrays.diff"), tested="untested: equivalent control flow, not built.",
       tradeoffs="Two more locals; still needs the NULL-on-entry for the Fortran interface; does not cover the distributed twin by itself.",
       preferred=False, maintainer_fit="More lines for the same effect; he uses the output pointer directly elsewhere in libscotchmetis."),
 ],
 patch_files=[p3, p4],
 cleanup_done="The `SCOTCH_graphInit()` call before the mesh build was moved after it (no graph to exit on a mesh failure); the hard `return (METIS_ERROR)` in the debug branch is gone; nothing left unused.",
 test_added="" + "none: src/check has no failing-allocation tests (precedent: no OOM test anywhere in src/check); the reproducers under repro/CLI-15 cover it.",
 docs_updated="",
 needs="", needs_note="",
 notes="The meshGraphDual double free found while fault-injecting this item is PS2-G26-1 (patch 0004, also graphLoad/Chaco/meshGraphNodal).",
))

items.append(dict(
 id="CLI-09",
 our_title="ParMETIS_V3_NodeND status tied to the sizes tree, not to the ordering it computed",
 status="still-present", method="partly-run",
 ran=("ASan base-combined build, $WORK/repro/CLI-09/pn_firstpass.c (16x16 grid), ASAN_OPTIONS=detect_leaks=0 mpirun --oversubscribe:\n"
      "  -np 3 -> rank 0/3 sizes=buf: ret=-4 (METIS_OK=1) order range [0,244]; ranks 1,2 ret=-4 too; -np 1,2,4 -> ret=1\n"
      "  -np 1,2,4 with sizes=NULL -> ret=-4 on every rank although order is filled.\n"
      "Completeness of the order at np=3: the shipped test_libparmetis_v3 (checkOrder gathers the permutation and checks bijectivity) on data/bump.grf: base -> 'main: error in ParMETIS_V3_NodeND', mpirun exit 1 (the ordering itself passes checkOrder only because the program exits before); patched -> exit 0 at np=3 and np=4, and the new checkSizes() verifies sizes sums to vertglbnbr at np=4 and is all -1 at np=3. " + CHECKS),
 read_only="The 'METIS_OK on failed Compute/Perm' half: after the patch `o` stays METIS_ERROR unless both calls return 0; forcing a failure inside PT-Scotch's distributed ordering was not attempted.",
 why_not_run="No cheap fault point inside SCOTCH_dgraphOrderCompute() on a valid graph (its allocations happen on every process and MPI's tens of thousands of allocations make a blind sweep impractical).",
 severity="medium",
 severity_note="Public ParMETIS API: a correct call on 3, 5, 6... processes returns an error code that MUMPS/PETSc-style callers treat as fatal; same as the review.",
 location_7_0_17="src/libscotchmetis/parmetis_dgraph_order.c:122 (o = METIS_ERROR), :150-151 (Compute/Perm unchecked), :206-210 (o = METIS_OK only inside the sizes/power-of-two branch)",
 evidence=("7.0.17 :150-151 `SCOTCH_dgraphOrderCompute (&grafdat, &ordedat, &stradat); SCOTCH_dgraphOrderPerm (&grafdat, &ordedat, order);`\n"
           ":206-209 `if ((rootnum >= 0) && (sizes != NULL)) { memSet (sizes, 0, ...); _SCOTCH_ParMETIS_V3_NodeNDTree (...); o = METIS_OK; }`\n"
           "doc/src/ptscotch/p_l.tex:5196-5204: 'this routine will compute an ordering even when the number of processors ... is not a power of two ... else [sizes] is filled with -1 values'"),
 upstream_change="",
 review_accuracy="Accurate. ParMETIS 4.0 (libparmetis/ometis.c) returns METIS_OK unless the input check fails, fills `sizes` (2*npes entries: npes subdomain sizes then separators) and has no power-of-two restriction (it rounds the level count down); Scotch's doc keeps its -1 convention for non-powers of two, which the patch preserves.",
 first_pass_critique="Status/evidence right. Its sketch sets o = METIS_OK only after Perm but leaves the separator-tree block running regardless of the ordering status (it would walk an incomplete ordering); it proposes no test although check_libparmetis_v3 runs only with 4 processes (EXECP4) and so never saw the non-power-of-two failure.",
 extra_instances=[
  dict(location="src/libscotchmetis/parmetis_dgraph_order.c:106,108,242,244 (stale comments: options 'not used' is true, sizes 'not used' is false)", quote="SCOTCH_Num * const sizes, /* Of size twice the number of processors ; not used */", covered_by_patch=True),
  dict(location="src/libscotchmetis/parmetis_dgraph_order.c:174 (trailing whitespace line)", quote="               ", covered_by_patch=True),
 ],
 fix_options=[
  dict(label="Status from Compute/Perm; sizes best effort, tree walked only on success (chosen)",
       summary="`o = METIS_OK` iff both ordering calls return 0; the separator-tree block runs only then and when the process count is a power of two; the inner `o = METIS_OK` is removed; sizes keep their -1 preset otherwise. check_libparmetis_v3 gains a 3-process run (Makefile + CMake) and checkSizes().",
       diff_file=p5, tested="pn at np=1..4 with/without sizes; test_libparmetis_v3 at np=3 and 4 in both trees.",
       tradeoffs="Behaviour change: non-power-of-two runs now return METIS_OK (documented behaviour); callers that used the error to detect 'no sizes' must test sizes[0] == -1 instead (as the doc says).",
       preferred=True, maintainer_fit="Matches his p_l.tex description of the routine; the test addition follows 261f1c7 (Add tests for libparmetis) and the EXECP3 lines of check_prog_dgord."),
  dict(label="Same status, but zero the sizes array when the tree is not as expected",
       summary="Always memSet sizes to 0 when the ordering succeeded and the process count is a power of two, even if the tree walk is skipped (rootnum < 0).",
       diff_file=A("CLI-09-b-status-from-ordering-zero-sizes-on-failure.diff"), tested="untested: not built.",
       tradeoffs="Reports zeros (a plausible but wrong tree) instead of the documented -1 sentinel when the tree is malformed.",
       preferred=False, maintainer_fit="Contradicts the doc's -1 convention."),
  dict(label="Keep METIS_ERROR when no sizes can be returned, only fix the unchecked calls",
       summary="Skip the tree block if Compute/Perm fail; otherwise unchanged.",
       diff_file=A("CLI-09-c-keep-error-when-no-sizes.diff"), tested="untested: not built.",
       tradeoffs="Keeps the documented-but-false 'error' for 3 processes; minimal diff.",
       preferred=False, maintainer_fit="Leaves the review's main complaint in place."),
 ],
 patch_files=[p5],
 cleanup_done="Inner `o = METIS_OK` removed; stale 'not used' comments on `sizes` fixed; trailing whitespace at :174 removed.",
 test_added="src/check/test_libparmetis.c: checkSizes() (sum of the 2p-1 sizes == vertglbnbr when p is a power of two, all -1 otherwise); src/check/Makefile + CMakeLists.txt: test_libparmetis_v3 also run with 3 processes (EXECP3 / MPIEXEC 3).",
 docs_updated="",
 needs="", needs_note="",
 notes="With sizes != NULL on some processes only, the collective CblkDist/TreeDist calls still run on all of them (unchanged), so the fix introduces no new collective mismatch.",
))

items.append(dict(
 id="CLI-10",
 our_title="esmumps2 ignores ordering and factorization failures, returns 0 with unwritten nv/pe",
 status="still-present", method="ran",
 ran=("Plain build of base-combined + LD_PRELOAD injector, $WORK/repro/CLI-10/es_fail.c (8x8 grid, Fortran-based, sentinels in nv):\n"
      "  FAILMALLOC_AT=8 ./es_fail 8 -> ERROR: orderGraphListStrat: out of memory / esmumps returned 0; nv written 0/64, pe in output form 0/64\n"
      "  N=9..11, 16..40 (strategy parser OOM): same 'returned 0; nv written 0/64'. N=7 (vendtab): returned 1 (already handled).\n"
      "  patched: ERROR: esmumps2: cannot compute ordering / esmumps returned 1; nv written 0/64. " + CHECKS),
 read_only="", why_not_run="",
 severity="high",
 severity_note="Raised from medium: MUMPS consumes pe/nv as the elimination tree; a silent 0 after OOM means a wrong factorization structure, not a diagnostic. Only reachable on allocation failure.",
 location_7_0_17="src/esmumps/esmumps.c:140 (graphBuildGraph2), :143 (orderGraph), :171 (symbolFaxGraph), :155 (ORDER_DUMP return leaks), :235 (return (0))",
 evidence=("7.0.17 :139-143 `graphInit (&grafdat); graphBuildGraph2 (&grafdat, 1, n, pfree - 1, ...); orderInit (&ordedat); orderGraph (&ordedat, &grafdat);`\n"
           ":170-171 `symbolInit (&symbdat); symbolFaxGraph (&symbdat, &grafdat, &ordedat);` ... :235 `return (0);`\n"
           "order_scotch_graph.c:169-172 on OOM: `orderExit (ordeptr); orderInit (ordeptr); return (1);` so the symbolic factorization runs on an empty ordering (cblknbr = 0) and the fill loop does nothing."),
 upstream_change="",
 review_accuracy="Accurate on the mechanism. Its 'MUMPS-style negative code' is not what MUMPS checks: MUMPS 5.7.3 src/ana_orderings_wrappers_m.F:445 and :575 test `IF (NCMPA .NE. 0)` and set INFO(1) = -88; the existing +1 convention is therefore the right one to keep.",
 first_pass_critique="Correct status, reproduction and choice of +1. Its diff duplicates the cleanup sequence three times (he uses fail labels, e.g. dgraphInduce2 in 7.0.17) and leaves the ESMUMPS_ORDER_DUMP `return (1)` leaking the graph, ordering and vendtab.",
 extra_instances=[
  dict(location="src/esmumps/esmumps.c:153-156 (ESMUMPS_ORDER_DUMP: fopen failure returns 1 without freeing vendtab/graph/ordering)", quote="errorPrint (\"esmumps2: cannot open ordering dump file\"); return (1);", covered_by_patch=True),
  dict(location="src/esmumps/esmumps.c:171 comment typo 'factorizaion'", quote="/* Compute block symbolic factorizaion */", covered_by_patch=True),
 ],
 fix_options=[
  dict(label="Check the three steps, fail labels, keep returning 1 (chosen)",
       summary="`if (graphBuildGraph2 (...) != 0) { errorPrint; fail1: graphExit; memFree (vendtab); return (1); }`, `fail2:` after orderGraph (orderExit then goto fail1), symbolFax failure does symbolExit then goto fail2; ORDER_DUMP fopen failure goes to fail2; 'It returns' block added to the routine comment.",
       diff_file=p6, tested="es_fail sweep before/after; check_libesmumps and make escheck in both trees; test_esmumps (plain, errorexit-linked) under injection exits 1.",
       tradeoffs="No ABI change (0/1 as before); jumps into blocks, as the maintainer does.",
       preferred=True, maintainer_fit="Label idiom and numbering from scotch_maint7.0 2.1.3 and his dgraphInduce2 rewrite (fail1 inside the first failing block); same error value as the routine's existing OOM path."),
  dict(label="Negative error code (-1), test keeps `ncmpa < 0`",
       summary="Same checks and labels but `return (-1)` everywhere, as the review suggests.",
       diff_file=A("CLI-10-b-negative-return-code.diff"), tested="untested: not built.",
       tradeoffs="Changes the value Fortran callers have seen since 2001 for the vendtab OOM; MUMPS tests `.NE. 0` so nothing is gained; the C test_libesmumps tests `!= 0` already.",
       preferred=False, maintainer_fit="He would not change an ABI-visible value without a reason; MUMPS source shows there is none."),
 ],
 patch_files=[p6],
 cleanup_done="No field or symbol made unused; the comment block now documents the return values.",
 test_added="none in src/check: no OOM test exists there (test_libesmumps.c already tests `esmumps (...) != 0`); repro/CLI-10 covers it.",
 docs_updated="",
 needs="", needs_note="",
 notes="MUMPS source (5.7.3) was downloaded to verify the convention: mumps_scotch.c:120-133 stores the esmumps/esmumpsv return in *ncmpa; ana_orderings_wrappers_m.F:445 `IF (NCMPA .NE.0) THEN ... INFO(1) = -88`.",
))

items.append(dict(
 id="CLI-22",
 our_title="test_esmumps only fails on negative ncmpa while esmumps returns +1; %d for INT",
 status="still-present", method="ran",
 ran=("Plain tree, $WORK/repro/CLI-22: the base-combined test_esmumps.c and the patched one, both linked against the PATCHED libesmumps (returns 1 on a failed ordering) and the non-exiting error library, injector FAILMALLOC_AT=10 on data/bump.grf:\n"
      "  pristine driver: ERROR: orderGraphListStrat: out of memory / ERROR: esmumps2: cannot compute ordering / exit=0 (error missed)\n"
      "  patched driver : ... / ERROR: test_esmumps: error in ESMUMPSF (1) / exit=1\n"
      "With the shipped link line (-lscotcherrexit, Makefile and CMake) the program exits 1 at the first errorPrint, before the ncmpa test ($WORK/plain/src/esmumps/test_esmumps under injection: exit=1), which is why the defect is latent in both build systems."),
 read_only="", why_not_run="",
 severity="low",
 severity_note="Test driver only, and masked by the errorexit library it is linked with; the sign convention is not a library bug (MUMPS tests .NE. 0).",
 location_7_0_17="src/esmumps/test_esmumps.c:146-147; src/esmumps/esmumps.c:134 (return (1)); src/esmumps/library_esmumps_f.c:81 (*ncmpa = esmumps (...))",
 evidence="7.0.17 test_esmumps.c:146-147 `if (ncmpa < 0) { errorPrint (\"test_esmumps: error in ESMUMPSF (%d)\", ncmpa);`; esmumps.c:133-134 `errorPrint (\"esmumps2: out of memory\"); return (1);`",
 upstream_change="",
 review_accuracy="Accurate on the inconsistency and the %d; wrong on the remedy: the MUMPS convention is 'non-zero is an error' (MUMPS 5.7.3 ana_orderings_wrappers_m.F:445), so the test must test `!= 0`, not the library return -1. It also misses that the driver is linked with -lscotcherrexit, which hides the defect.",
 first_pass_critique="Follows the review into the negative-code convention ('ncmpa != 0 is not right either: ncmpa is a compression count on success'): wrong, esmumps2() always returns 0 on success, there is no compression count; the AMD meaning of NCMPA does not apply to the Scotch wrapper, and MUMPS itself requires NCMPA == 0 from it.",
 extra_instances=[],
 fix_options=[
  dict(label="Test `ncmpa != 0` and print with INTSTRING (chosen, in the CLI-10 commit)",
       summary="One condition and one format change in test_esmumps.c, comment stating that ESMUMPSF returns 0 on success as MUMPS expects.",
       diff_file=p6, tested="see ran; also compiled in both trees by `make esmumps` (test_esmumps is built by the esmumps `scotch` target).",
       tradeoffs="None.", preferred=True, maintainer_fit="Keeps the library ABI; matches test_libesmumps.c's `!= 0` test."),
  dict(label="Negative library code, test unchanged except INTSTRING",
       summary="See CLI-10 option b.", diff_file=A("CLI-10-b-negative-return-code.diff"), tested="untested: not built.",
       tradeoffs="ABI-visible change for no gain.", preferred=False, maintainer_fit="See CLI-10."),
 ],
 patch_files=[p6],
 cleanup_done="none needed",
 test_added="(the file is the test)",
 docs_updated="",
 needs="", needs_note="",
 notes="library_esmumps_f.c needs no change: it already propagates esmumps()'s 0/1 into ncmpa, which is what MUMPS checks.",
))

items.append(dict(
 id="BLD-19",
 our_title="esmumpsv() never tested: test guarded by a macro no build system defines",
 status="still-present", method="ran",
 ran=("`git grep -n ESMUMPS_HAS_ESMUMPSV` on base-combined: only src/check/test_libesmumps.c:181 and :196. With the guard removed: check_libesmumps (data/bump.grf without weights, data/bump_imbal_32.grf with weights, which runs the esmumpsv() branch and checkEsmumps()) passes in the 32-bit and 64-bit ASan trees, and `make escheck` at the top level passes in both (logs $WORK/build*.check_esmumps.log, $WORK/build*.escheck.log)."),
 read_only="", why_not_run="",
 severity="low", severity_note="Test gap only; agrees with the review.",
 location_7_0_17="src/check/test_libesmumps.c:181 and :196",
 evidence="7.0.17 test_libesmumps.c:181 `#ifdef ESMUMPS_HAS_ESMUMPSV` ... :196 `#endif /* ESMUMPS_HAS_ESMUMPSV */`; src/esmumps/library.h:59 declares esmumpsv unconditionally.",
 upstream_change="",
 review_accuracy="Accurate.",
 first_pass_critique="Correct (status, grep, the bump_imbal_32 observation and the preference for removing the guard).",
 extra_instances=[],
 fix_options=[
  dict(label="Remove the guard (chosen)", summary="Delete the #ifdef/#endif, keep the `velotab != NULL` condition with a comment.",
       diff_file=p7, tested="check_libesmumps + escheck, both trees.", tradeoffs="None: the symbol has been public since 6.1.", preferred=True,
       maintainer_fit="Nothing in src/check is conditional on build-system macros except SCOTCH_METIS_VERSION; the macro was a leftover."),
  dict(label="Define the macro in the check Makefile and CMake", summary="Explicit compile rule for test_libesmumps with -DESMUMPS_HAS_ESMUMPSV, target_compile_definitions in CMake.",
       diff_file=A("BLD-19-b-define-macro-in-build-systems.diff"), tested="untested: not built.", tradeoffs="Adds a special-case compile rule to two build systems for a guard that protects nothing.", preferred=False,
       maintainer_fit="He removed similar dead conditionals rather than feeding them."),
 ],
 patch_files=[p7],
 cleanup_done="The macro no longer exists anywhere in the tree.",
 test_added="(the file is the test; the weighted branch now always compiles and runs on bump_imbal_32.grf)",
 docs_updated="", needs="", needs_note="", notes="",
))

items.append(dict(
 id="BLD-17",
 our_title="make -j esmumps ptesmumps builds libesmumps twice concurrently in one directory",
 status="still-present", method="ran",
 ran=("$WORK/race (copy of the 32-bit ASan tree with scotch/ptscotch built), 6 runs of `(cd esmumps; make clean); rm ../lib/*esmumps*; make -j8 esmumps ptesmumps` ($WORK/repro/BLD-17/base_run1..6.log):\n"
      "  base: src/esmumps entered 8 times, `gcc -shared -o libesmumps.so` 2 times in 6/6 runs, `-c dof.c` compiled twice in runs 2 and 4 (concurrent compilers on the same dof.o); no hard failure in 6 runs.\n"
      "  patched (fixed_run1..6.log): entered 6 times, dof.c once, libesmumps.so linked once, 6/6; `make -j scotch ptscotch esmumps ptesmumps` (the ci/build_makefile.sh line, fixed_ci.log) builds libesmumps.so and libptesmumps.so with one link; `make -j8 ptesmumps` alone (fixed_pt.log) installs both libraries. Full rebuilds with the new Makefiles in build, build64 and plain: rc=0, 0 warnings."),
 read_only="", why_not_run="",
 severity="medium", severity_note="CI and any parallel user build; corruption of libesmumps.a/.so is timing dependent (not observed in 12 runs, duplicate concurrent compilation and linking is).",
 location_7_0_17="src/Makefile:122-129 (`ptesmumps : scotch ptscotch` -> `$(MAKE) ptscotch && $(MAKE) ptinstall`); src/esmumps/Makefile:61 (`ptscotch : scotch`), :68 (`ptinstall : scotch`)",
 evidence="src/Makefile:128-129 `ptesmumps : scotch ptscotch` / `(cd esmumps ; $(MAKE) ptscotch && $(MAKE) ptinstall)`; src/esmumps/Makefile:61 `ptscotch : scotch`",
 upstream_change="",
 review_accuracy="Accurate, including the fix line.",
 first_pass_critique="Correct reproduction (dof.c twice in 5/8 runs) and preferred option; it left esmumps/Makefile untouched, where `ptinstall : scotch` was the odd one out (every other directory has `ptinstall : ptscotch`).",
 extra_instances=[
  dict(location="src/Makefile:99-108 (`ptscotch` does not depend on `scotch`, so `make -j scotch ptscotch` runs `make scotch` and `make ptscotch` concurrently in libscotchmetis; same shape, G30's BLD-11)", quote="ptscotch : libptscotch / (cd libscotchmetis ; $(MAKE) ptscotch && $(MAKE) ptinstall)", covered_by_patch=False),
 ],
 fix_options=[
  dict(label="`ptesmumps` depends on `esmumps` and only runs `ptinstall`; `ptinstall` depends on `ptscotch` (chosen)",
       summary="Two-line change in src/Makefile, one in src/esmumps/Makefile (+ copyright year).",
       diff_file=p8, tested="see ran.", tradeoffs="`make ptesmumps` now also installs libesmumps (same archive, harmless).", preferred=True,
       maintainer_fit="src/Makefile already orders targets by prerequisites (`escheck : esmumps`); `ptinstall : ptscotch` is the pattern of scotch/Makefile:76 and libscotchmetis/Makefile:85."),
  dict(label="Make esmumps/Makefile's `ptscotch` build the library itself without `scotch`",
       summary="`ptscotch` builds libesmumps only (no test programs), `ptinstall : ptscotch`; src/Makefile keeps running `ptscotch && ptinstall` but after `esmumps`.",
       diff_file=A("BLD-17-b-esmumps-makefile-independent-ptscotch.diff"), tested="untested: not built.", tradeoffs="Two recipes to maintain for one library; still needs the top-level dependency to be safe.", preferred=False,
       maintainer_fit="More Makefile text for the same serialization."),
  dict(label="Serialize in CI only", summary="ci/build_makefile.sh builds ptesmumps in a second make.", diff_file=A("BLD-17-c-serialize-in-ci-only.diff"), tested="untested (ci/ is G30's).",
       tradeoffs="Users running `make -j esmumps ptesmumps` still race.", preferred=False, maintainer_fit="Hides the defect."),
 ],
 patch_files=[p8],
 cleanup_done="none needed (the `ptscotch` target of src/esmumps/Makefile is kept: it is the documented standalone goal and `ptinstall` now depends on it).",
 test_added="" + "none: no Makefile tests exist; repro/BLD-17 logs are the evidence.",
 docs_updated="", needs="", needs_note="",
 notes="ci/ not edited (G30). The CI line still works unchanged (fixed_ci.log).",
))

json.dump(items, open(W + "/audit.json", "w"), indent=1)
print("ok", len(items))
