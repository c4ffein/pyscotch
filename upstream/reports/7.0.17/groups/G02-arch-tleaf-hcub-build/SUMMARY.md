# G02-arch-tleaf-hcub-build -- summary (Scotch 7.0.17: tleaf/ltleaf/hcub loaders and builders, generator shifts)

Series: patches/0001..0004, applied AFTER G01-arch-sub-dist's five (git am on a fresh v7.0.17 clone: 9 commits apply); overlaps with G01: test_scotch_arch.c, arch_sub.c (one cast).
| id | status | method | severity | patch |
|---|---|---|---|---|
| COR-06 | still-present | ran | medium | patches/0002-Bugfix-validate-tree-leaf-architectures-in-one-place.patch |
| COR-19 | partially-fixed (c5baef9 bound only) | ran | low | patches/0003-Bugfix-shift-architecture-sized-values-not-ints-by-h.patch |
| PS-API-3 | still-present | ran | low | patches/0003 |
| API-10 | still-present | ran | medium | patches/0002 + 0003 |
| PS-API-2 | still-present | ran | low | patches/0001-Declare-SCOTCH_archLtleaf-in-the-library-header-repo.patch |
| PS-API-4 | still-present (mechanism corrected: leak, not a crash) | partly-run | info | patches/0002 |
| CLI-24 | still-present | ran | low | patches/0003 |
| COR-07 (tleaf half) | still-present (leak sub-claim no longer true) | ran | medium | patches/0002 |
| PS2-G02-...-1 (new) cmpltw frees caller's array | still-present | ran | medium | patches/0004-Bugfix-free-the-right-array-on-invalid-weights-in-ar.patch |
| PS2-G02-...-2 (new) scotchfarchltleaf documented, missing | still-present | ran | low | alt/PS-API-2-B-fortran-twin.diff (G17) |
| PS2-G02-...-3 (new) sbbt strategy shift | still-present | source-read | low | alt/PS2-G02-3-sbbt-bound.diff (DMO file) |
| PS2-G02-...-4 (new) archSubArchBuild orgtermnbr+1 overflow | still-present | ran | info | alt/PS2-G02-4-sub-treetab-size.diff (G01 file) |
Three most important facts
1. COR-06/COR-07/API-10/PS-API-4 are one design defect: four copies of the tleaf/ltleaf construction code with different checks. Patch 0002
   gives each class ONE Build routine (archTleafArchBuild, archLtleafArchBuild, archHcubArchBuild in 0003) used by the file loader and the
   library builder, with unconditional checks (levels >= 1, sizes >= 2, links >= 1, terminal count fits in Anum, permutation size on a level
   boundary, indices in range and unique), fields published only on success, Free tolerant of an empty body; loaders free nothing (archLoad
   does, as d555f2c relies on). test_scotch_arch gains an ltleaf whose permutation spans two levels.
2. COR-19 is only half fixed upstream: with 64-bit Anum, 'hcub 31'..'hcub 62' pass the new bound and compute int shifts (UBSan at
   arch_hcub.c:261, size 256 for dimension 40). Patch 0003 shifts the target type at all 20 sites of this class in the tree (arch_hcub,
   arch_sub, arch_deco2, kgraph_band, kgraph_map_rb x2, dgraph_build_hcub, five generators) and bounds each generator so that every value it
   computes fits (32-bit limits: amk_hy 29, gmk_hy 25, gmk_ub2 28, amk_fft2 14, amk_ccc 24; 64-bit: 61/57/60/30/56), verified under UBSan.
3. New medium defect: SCOTCH_archCmpltw with a weight <= 0 frees the CALLER's array (arch_cmpltw.c:184 memFree (velotab)) and leaks its own;
   ASan double-free from a 10-line program. Patch 0004 (one token).

Verification: 32/64-bit ASan+UBSan trees, 0 warnings, touched files also compiled with -DSCOTCH_DEBUG_ALL; check_scotch_arch(_deco),
check_prog_atst/amk/amk_grf/gmk/gmap clean on both; check_scotch_arch_build / graph_map show only the pre-existing archDecoArchBuild2 leak and
bgraph_bipart_ml/kgraph_map_ml null-offset UBSan (same as pristine). Fuzzing 2000 mutated tleaf/ltleaf/hcub/sub strings: 32-bit 29 -> 6
sanitizer signatures, 64-bit 36 -> 3 (remaining: intLoad overflow, another group, and the two arch_sub cases above). Malloc-failure sweep on
plain trees clean before and after. stylecheck and git diff --check clean. Reproducers with commands in repro/<ID>/README.
Could not do: malloc-failure injection under ASan (ASan owns malloc; PS-API-4's leak is source-established, its 'crash' claim refuted at
runtime); PS2-...-3 (sbbt) compiled with mpicc, not run (needs a distributed run with a custom strategy, DMO-10's file); no negative tests
in src/check (no precedent). User must decide: fold the Fortran twin (alt/PS-API-2-B) here or leave it to G17; sbbt bound to DMO's series
or not; per-tool generator bounds (five commented constants, as shipped) vs one uniform '(bits-3)/2' bound.
