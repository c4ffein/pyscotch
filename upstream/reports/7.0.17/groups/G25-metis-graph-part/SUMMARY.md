# G25-metis-graph-part — summary (patches on v7.0.17: $WORK/patches/0001..0006)

CLI-02 still-present ran high   -> 0003-Bugfix-convert-MeTiS-v5-partitioning-parameters-into.patch
CLI-03 still-present ran high   -> 0003 (same commit; ParMETIS twin + doc p_l.tex + tests)
CLI-06 still-present ran high   -> 0004-Bugfix-handle-default-values-in-MeTiS-v5-option-arra.patch
CLI-07 still-present ran medium -> 0003 (first constraint gathered; ParMETIS stride + ubvec)
CLI-08 still-present ran high   -> 0002-Bugfix-bound-the-renormalization-factor-when-convert.patch (+0001)
CLI-19 still-present ran medium -> 0005-Bugfix-select-the-partitioning-objective-from-option.patch
PS2-G25-1 (new) still-present ran high -> 0001-Bugfix-free-proper-array-on-invalid-target-weight-in.patch
PS2-G25-2 (new) info source-read -> no patch (dead v5 block in test_libparmetis.c)
0006-Style-fix.patch: tab / missing space at metis_graph_part.c SCOTCH_archExit call.

Three most important facts
1. All six leads are real in 7.0.17 (nothing in libscotchmetis changed in 7.0.16..7.0.17) and were reproduced in the
   32-bit and 64-bit ASan trees; the patched series passes check_libmetis_{v3,v5,dual_v3,dual_v5,dual_f_v3,dual_f_v5},
   check_libparmetis_v3, check_scotch_arch, check_scotch_graph_map in both trees with 0 build warnings; `git am` clean.
2. New libscotch defect PS2-G25-1: arch_cmpltw.c:184 frees the CALLER's weight array on a non-positive weight (regression
   of 530f3f2, July 2026). Any SCOTCH_archCmpltw user, and every METIS/ParMETIS tpwgts path (CLI-08), double-frees.
3. The shared conversion lives in one static routine `_SCOTCH_METIS_V5_PartGraph()` (both V5 wrappers) plus
   `_SCOTCH_METIS_optionGet()` in metis_options.c (new metis_options.h, Makefile deps; CMake needs nothing). The ParMETIS
   library cannot share code with libscotchmetis (separate library, float arrays), so its wrapper gets the same logic
   inline, mirroring the sequential idiom; the PT-Scotch manual paragraph that documented the wrong behaviour is updated.

Could not do / decisions for the user
- METIS_OPTION_UFACTOR (METIS's default-tolerance option when ubvec is NULL) is still ignored; adding it is a feature
  that changes the documented "only NUMBERING and OBJTYPE are supported" statement. Default stays 0.01 (PT-Scotch 0.05).
- ubvec[0] <= 1.0 now returns METIS_ERROR_INPUT (as METIS does); the shipped test used 0.05 and was changed to 1.05.
  A negative test for this was not added because src/check has no failing-call tests (precedent 2bcd53c).
- OBJTYPE=VOL is honoured for PartGraphRecursive too, although real METIS rejects it there (assumption stated in audit).
- PartMeshDual's own vsize||OBJTYPE output selection and its NULL - baseval (CLI-05) are G26's lines; my CLI-06 hunk in
  that function touches only the baseval lines (:108-109).
- The checkLoad() bound (1.5 x target on the first constraint) is loose on purpose: patched runs give 1.00-1.03,
  pristine 1.76-2.47 on the three test graphs.
