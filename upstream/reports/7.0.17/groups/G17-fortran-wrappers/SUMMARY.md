# G17-fortran-wrappers -- summary (Scotch 7.0.17: Fortran API wrappers, manuals' Fortran synopses, Fortran METIS test)

Series: patches/0001..0007 on v7.0.17 (git am verified on a fresh clone, 7 commits; also G02 0001 + these 7 = 8 commits).
0007 (scotchfarchltleaf) compiles only with G02's 0001 (SCOTCH_archLtleaf declaration in library.h); alt/API-24-C is the standalone form.
| id | status | method | severity | patch |
|---|---|---|---|---|
| API-01 | fixed-in-7.0.17 (complete: 0 ORDER findings over 244 wrappers) | ran | high | - |
| API-05 | fixed-in-7.0.17 (complete: 0 BYVALUE findings) | ran (dgraphband source-read) | high | - |
| API-09 | still-present | ran | medium | patches/0001 |
| API-11 | still-present | ran | medium | patches/0002 |
| PS-API-6 | still-present | source-read (doc) | low | patches/0006 |
| API-13 | still-present (64-bit only) | ran | medium | patches/0003 |
| API-24 | still-present (13 + 4 misspelled = 17 undefined documented routines) | ran | low | patches/0004 + 0007 (+0006 for the 4 names) |
| BLD-20 | still-present | ran | low | patches/0005 |
| PS2-G17-1..7 (new) | grid3d debug-only checks (SIGFPE), dmeshBuildAdm synopses wrong, 9 missing ierr, type typos, 12 undocumented wrappers, METIS v5 Fortran undocumented, leaky Fortran test | see extra.json | low/info | 0006 covers 2,3,4; alt/ for 1 |
Three most important facts
1. The group is one audit, not five fixes: repro/fortran_audit.py cross-checks all 244 SCOTCH_FORTRAN/FORTRAN wrappers against the 247 C
   prototypes, the 218 C definitions and the 231 Fortran synopses of both manuals (name case, by-value scalars, forwarding order, parameter
   types vs C and vs manual, trailing ierr, argument count, missing wrappers, missing/misspelled synopses, doc-vs-C order). Pristine: 114
   findings; after the series: 57, all accounted for (METIS v3-only doc, undocumented wrappers, DOCC false positives on variadic/array
   prototypes). The maintainer can re-run it on any tree.
2. Code defects are few and mechanical (API-09 one token, API-11 ierr, API-13 one type) and were exercised from real gfortran/mpifort
   programs on 32- and 64-bit ASan trees (repro/API-09, repro/API-24/seq_f.f90 + C twin, par_f.f90). The 13 missing wrappers never
   existed; they are added beside their neighbours (0004), one in a new library_dgraph_grow_f.c registered in Makefile and CMakeLists.
3. The manuals are the larger problem: beyond PS-API-6, six misspelled Fortran names, nine synopses without ierr, SCOTCH_dmeshBuildAdm's
   synopses describing a different routine, and a dozen type typos; all fixed in one documentation commit (0006).
Verification: 32/64-bit ASan+UBSan trees build with 0 warnings; full `check` (incl. the 3 Fortran targets) and `ptcheck` pass on 32-bit;
the 3 Fortran check targets pass on 64-bit (mesh_build_f needs detect_leaks=0 because of its own pre-existing leak, PS2-G17-7);
stylecheck and git diff --check clean on every touched C file; corrupted BLD-20 test exits 1.
Could not do: no src/check test added for the wrappers (no Fortran test harness exists for the sequential or PT-Scotch API; the functional
programs live in repro/API-24); PS2-G17-1 diff not committed (dgraph_build_grid3d.c belongs to the DGR groups).
User must decide: series order with G02 (G02 0001 before G17 0007, or use alt/API-24-C); 'integer*1' vs 'character' for SCOTCH_GraphPart2
in the manual (patch 0006 uses integer*1); whether to also document the 12 wrappers without a manual entry (PS2-G17-5, not written).
