# G01-arch-sub-dist -- summary (Scotch 7.0.17, target-architecture loaders)

| id | status | method | severity | patch |
|---|---|---|---|---|
| COR-02 | fixed-in-7.0.17 (d555f2c) | ran | high (7.0.16 only) | - |
| COR-03 | still-present | ran | high | patches/0002-Bugfix-always-check-terminal-numbers-when-building-s.patch |
| COR-04 | still-present | ran | high | patches/0001-Bugfix-clean-up-properly-on-sub-architecture-loading.patch |
| COR-05 | still-present | ran | high | patches/0003-Bugfix-allocate-and-own-the-original-architecture-wh.patch |
| PS-COR-3 | still-present | ran | low | patches/0001 (same commit as COR-04) |
| COR-27 | still-present | ran | low | patches/0004-Bugfix-alternate-matching-passes-in-archCmpltMatchMa.patch |
| PS2-G01-arch-sub-dist-1 (new) | still-present | ran | high | patches/0005-Bugfix-build-sub-architectures-made-of-a-single-term.patch |
| PS2-G01-arch-sub-dist-2 (new, info) | still-present | source-read | info | - |

Three most important facts
1. New high: a sub-architecture made of ONE terminal that is not vertex 0 crashes (file 'sub 1 3 cmplt 4', and the public
   SCOTCH_archBuild2 (graph, 1, {5}) twin): both callers hand archSubArchBuild2() the kept-vertex count instead of the array size.
   Patch 0005 fixes both callers (one token each) and adds the case to test_scotch_arch.c. It touches arch_deco2_build.c:653 (deco group's file).
2. One ownership protocol for both meta-architectures (sub, dist), consistent with d555f2c: the loader NULLs its fields, stores each
   allocation in the body as soon as it exists (inner Arch archInit()ed first), frees nothing itself -- archLoad() frees through the
   class hook, which tolerates NULL fields; Build sets the body only on success and frees everything on failure (0001, 0003).
   COR-05 design question answered: own the inner Arch (A), because archDistArchSave() already exists and 'dist' is a registered,
   loadable class; rejecting (alt B, provided) is right only if he declares dist internal-only (then Save should go too); 'dist' has
   had no caller since 6.0 (extra PS2-...-2), so removal (C) is a possible but larger decision for him.
3. COR-27: alternation now works and cmpltw/cmpltws share the matcher; test_scotch_arch.c gets 'cmplt 9' and a toggle-only half-fix
   is shown to fail that test. No golden outputs move (no check target maps onto an odd sub-architecture).

Verification: 32/64-bit ASan+UBSan and SCOTCH_DEBUG_ALL trees, 0 warnings; check_scotch_arch/_build/_deco, graph_map(_copy),
prog_atst/amk/amk_grf/acpl/gmap/gpart(_overlap/_remap/_clustering): identical to pristine (only hits: UBSan null offset in
bgraph_bipart_ml.c:195/kgraph_map_ml.c:239, LSan leak of test_scotch_arch_build in archDecoArchBuild2 -- pre-existing, other groups).
LD_PRELOAD malloc-failure sweep over every allocation of sub/dist loads: clean. git am on a fresh clone, stylecheck, diff --check: clean.

Could not do / caveats
- No negative tests in src/check (no precedent: every test_*.c must succeed and the error library prints to stderr); reproducers in repro/.
- No test for 'dist' (no public API builds one; the file round trip in test_scotch_arch.c only covers API-built architectures).
- Option C for COR-05 (remove dist) not written as a diff (14 files, design decision).

User must decide
- COR-05: A (own, recommended, patch 0003) vs B (reject, alt diff) vs C (remove). The series ships A.
- Patch 0005's one-token change in arch_deco2_build.c may overlap with the deco group's series; order the groups' patches accordingly.
- Whether to document 'dist' in s_f.tex now that it loads (not done: it stays undocumented).
