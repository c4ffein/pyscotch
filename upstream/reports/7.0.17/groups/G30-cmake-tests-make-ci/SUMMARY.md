# G30-cmake-tests-make-ci — SUMMARY (series based on the COMBINED series: base-combined = v7.0.17 + 142 commits; 13 commits on top, patches/0001..0013)

BLD-05  still-present  ran         low     -> patches/0007 (gmtst -o in gpart_overlap_2)
BLD-08  still-present  ran         medium  -> patches/0008 (';' -> '&&' in the three test_dgscat*)
BLD-09  still-present  ran         low     -> patches/0005 (scotchf.h/ptscotchf.h DEPENDS on library_f.h/library_pt_f.h)
BLD-10  still-present  ran         low     -> patches/0006 (suffix_fortran_file: file-level DEPENDS, *_tmp target removed)
BLD-11  still-present  partly-run  low     -> patches/0002 (parmetis.h + 65 libscotch rules + adm2dgr + gout; race not reproduced)
BLD-03  still-present  source-read high    -> patches/0009 (SONAR_TOKEN via job variables; no file, no -X log, nothing archived)
BLD-07  still-present  ran         medium  -> patches/0010 (set -o pipefail; dry run: old script exits 0 on #error, new exits 1)
BLD-14  still-present  partly-run  medium  -> patches/0010 (JOB_INT=64-64 rows; JOB_CMAKE_FLAGS + build/test_cmake_gcc_64 job)
BLD-21  still-present  source-read low     -> patches/0003 (+0004 for the FreeBSD '-std' typo)
PS2-G30-1 (the stale .so lead) still-present ran medium -> patches/0001 ($(?) -> $(^) in 7 library rules, libscotch + esmumps)
PS2-G30-2 FreeBSD '-std' -> 0004; PS2-G30-3 CMake duplicate custom rules (info, not patched); PS2-G30-4 Fortran test
unsuffixed -> 0011; PS2-G30-5 test_scotch_arch_build leaks (pristine too) -> 0013; PS2-G30-6 same test lacks module.h -> 0012.

Three most important facts
1. The .so lead is real and verified: with any *.shlib Makefile.inc, `touch graph.c; make scotch` relinks libscotch.so from graph.o
   alone (1387 -> 3 symbols) and every tool fails to link; CI never saw it because ci/Makefile.inc builds .a. After 0001 the
   incremental build works without deleting anything (both ASan trees). libscotchmetis already used $(^) since 2012.
2. The new CMake CI job (INTSIZE=64 IDXSIZE=64 SCOTCH_NAME_SUFFIX=_64 DETERMINISTIC=FULL), run locally, found two suffix
   breaks in src/check (PS2-G30-4/-6, both in pristine 7.0.17), fixed by 0011/0012: 100% of 179 tests passed (cm64 ctest rc=0, build warnings: only the pre-existing test_scotch_graph_induce.c memset one). Default-option CMake tree: 181/181.
3. Makefile trees (ASan, 32- and 64-bit Gnum) rebuilt from clean with 0 warnings; ptcheck and escheck pass; `make check` failed
   only at check_scotch_arch_build, a pre-existing test leak (PS2-G30-5, pristine 7.0.17 leaks identically); 0013 fixes it.

What I could not do
- No MinGW/Haiku/FreeBSD host (BLD-21, PS2-G30-2 are source-read; the '-std' error is reproduced with gcc here).
- No GitLab run (BLD-03 is deliberately not executed; BLD-07/14 scripts were dry-run locally with the lzma/bz2 flags stripped
  because those headers are absent on this box).
- src/esmumps/Makefile dependency additions left to G26 (alt/BLD-11-c-esmumps-deps-G26-owned.diff); 0001 does touch one line
  of src/esmumps/Makefile (the libesmumps rule) — trivial to rebase if G26 edits nearby.
- G29's ci/check_sources.sh (its patch 0005) IS wired into ci/build_cmake.sh by 0010 ('./ci/check_sources.sh || fatal'): merge
  G29's 0005 with it, or the CMake build jobs fail on the missing script. G29's PS2-G29-4 == PS2-G30-4, fixed by 0011. Merge order: G29's
  series applies on top of mine only with `git am -3` (plain am fails on the src/libscotch/CMakeLists.txt date line both bumped);
  on that G30+G29 tree ci/check_sources.sh exits 0 and ci/build_cmake.sh (with the hook) runs to completion, rc=0 (verify-hook.status).

User decisions
- BLD-03: SONAR_TOKEN env var needs SonarScanner CLI >= 4.7 on the 'sonar' runner; else use alt/BLD-03-b (-Dsonar.token).
  The token already archived in past artifacts must be rotated.
- BLD-14: the series adds 3 Makefile jobs (64-64) and 2 CMake jobs; drop rows if CI time matters.
- 0012/0013 touch src/check/test_scotch_arch_build.c (G02 finished; G28 owns test strictness): check for overlap when merging.
