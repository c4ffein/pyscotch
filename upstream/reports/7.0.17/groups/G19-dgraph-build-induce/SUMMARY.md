# G19-dgraph-build-induce: summary

DGR-05   still-present ran medium -> patches/0004 (procngbtab[2 * procnum])
DGR-12   still-present ran medium -> patches/0006 (per-vertex label collection, degree-sum check, 'unknown vertex label'; new src/check/test_scotch_dgraph_build.c) + 0005
DGR-06   still-present ran medium -> patches/0007 (proccnttab, as hdgraphInduceList 3436099)
PS-DGR-3 still-present ran low    -> patches/0008 (keep the old edge array when shrinking fails)
DGR-11   still-present ran medium -> patches/0010 (edge-end range, vertloctax >= baseval, hole ends 'arc end in numbering hole', loads always; 4 in-code cases in test_scotch_dgraph_check.c)
DGR-08   still-present ran medium -> patches/0009 (work arrays first, one fail label, return after the agreement, procsidtab attached after the final agreement)
DGR-18   still-present ran low    -> patches/0002 (flags |= after the build) + 0003
DGR-21   still-present ran low    -> patches/0001 (vertlocnnd; unused local removed)
Extra (extra.json): PS2-G19-1 grid builder hangs others on OOM -> 0003 (dgraphBuildHcub-style agreement); PS2-G19-2 dgraphBuild3 label path
hangs/disagrees on OOM, duplicate or unknown label in release builds -> 0005; PS2-G19-3 procsidtab leak -> 0009; PS2-G17-1 (forwarded)
grid3d parameter checks debug-only, SIGFPE on incrval 0 -> 0011; PS2-G19-4 (dgraph_io_load.c leak, G20), PS2-G19-5 (hcub leak, G02 file),
PS2-G19-6 (tree-wide unchecked shrinking memRealloc, incl. the sequential twin graph_induce.c): notes only.

Series: 11 commits on v7.0.17, `git am` clean on a fresh clone, stylecheck adds nothing (same 4 pre-existing hits), `git diff --check`
clean, 0 warnings on the 32-bit ASan, 64-bit and -DSCOTCH_DEBUG_ALL trees. All 15 CHECKPTSCOTCH targets (incl. the new
check_scotch_dgraph_build) pass on 32-bit and 64-bit (chk_32/chk_64_summary.txt: Makefile np=3, plus the dgraph test programs,
dgtst and dgpart with -np 1, 2, 4); the dgraph targets pass on the debug tree (chk_dbg_summary.txt). The only sanitizer hits are
pre-existing ones in other groups' files (library_dgraph_coarsen.c:163, bgraph_bipart_ml.c:195), identical to G18's logs.
Reproducers: repro/<ID>/README (fault injection via G18's LD_PRELOAD shim on UBSan-only trees; ASan trees for the others).

Three most important facts
1. Every allocation failure in dgraphBuild2 (rank >= P/2), dgraphInduce2 (any rank unless base 0 and rank 0), dgraphGhst2 (crash),
   dgraphBuildGrid3D and dgraphBuild3's label path hangs or crashes the whole job on pristine 7.0.17; after the series every one
   returns 1 on every rank (scan logs in the READMEs, np 1-4, base 0/1).
2. SCOTCH_dgraphBuild with vertex labels silently builds a wrong graph (rc=0, dgraphCheck fails) for any non-compact edge array,
   accepts labels that exist nowhere, and with np >= 3 a duplicate label on one process hangs the others. Fixed and regression-tested.
3. SCOTCH_dgraphCheck now rejects: edge ends outside [procvrttab[0], procvrttab[P]) (were accepted), ends in numbering holes
   (were an out-of-bounds read, ASan stack-buffer-overflow at dgraph_check.c:467), non-positive edge loads without a ghost array
   (were accepted), and vertloctax[v] < baseval. All shipped test graphs still pass.

Could not do / residual
- DGR-06's nth=3 injection still hangs inside dgraphHaloSync2 (dgraph_halo.c, G20's PS-DGR-2). Non-collective 'cannot allocate the
  dummy array' returns in dgraphBuild2/dgraphInduce2 kept, as the maintainer's own 'Cannot do a clean exit' (3c9b3ab).
- dgraph_build_hcub.c untouched (G02 collision); its inconsistent-parameters leak is PS2-G19-5, notes only.

User decisions
- Patch 0005 makes the two label-path agreements of dgraphBuild3 unconditional in release builds (two int Allreduces per labeled
  build), reversing the maintainer's explicit "Communication cannot be merged with a useful one"; same decision as G18's series.
- Patch 0010 changes what SCOTCH_dgraphCheck accepts (see fact 3): user graphs with zero edge loads now fail the checker.
