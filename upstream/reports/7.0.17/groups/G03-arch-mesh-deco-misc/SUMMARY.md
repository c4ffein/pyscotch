# G03-arch-mesh-deco-misc -- summary (Scotch 7.0.17)

| id | status | method | sev | patch |
|---|---|---|---|---|
| COR-07 (meshXD half) | still-present | ran | medium | patches/0002 |
| COR-14 | fixed-in-7.0.17 (feecf0d) | ran | medium | - |
| COR-21 | still-present | ran | low | patches/0002 + 0003 |
| COR-16 | still-present | ran | high | patches/0003 |
| PS-COR-1 | still-present | ran | medium | patches/0003 |
| COR-28 | still-present | ran | info | patches/0004 |
| COR-20 | still-present | ran | low | patches/0005 |
| PS2-G03-1 (new) | still-present | ran | low | patches/0003 |
| PS2-G03-2 (new) | still-present | ran | info | - (other group) |

Series on v7.0.17: 0001 is G25's PS2-G25-1 fix (archCmpltwArchBuild2 memFree), kept as base because
0002's arch_cmpltw.c hunk sits on top of it; 0002-0005 are this group's. `git am` on a fresh clone
and a clean 32-bit ASan build of the result both verified; 32- and 64-bit check targets pass.

Three most important facts
1. COR-16 is HIGH, not medium: a user `deco 1` file gives a heap-buffer-overflow (archDecoDomSize/
   DomDist) AND a stack-buffer-overflow (graphMapView2, negative distance), via public SCOTCH_archLoad.
   0003 propagates archDecoArchBuild2's result, makes its checks unconditional, adds a leaf check
   (PS-COR-1), validates the type-1 tree + distances, bounds termdommax. Mutation fuzzer over amk_*/
   acpl corpus: 43 distinct sanitizer sigs pristine -> 0 memory-safety sigs patched (repro/COR-16).
2. COR-07+COR-21 = one load-time validation commit (0002): reject meshXD dimnnbr<1, check every mesh/
   torus product and cmpltw weight sum vs ANUMMAX. First pass missed the archCmpltwArchBuild2 API twin
   and all three arch_deco.c instances (termdommax product + terminal weight sum = PS2-G03-1); covered.
3. COR-14 fully fixed upstream; verified the twin archTorusXDomDist still folds ON PURPOSE (torus wrap-
   around, matches torus2D/3D) and must NOT change.

Could not do / caveats
- No src/check regression test: harness requires every test to SUCCEED (G01 precedent); negative cases
  are in repro/<ID>/ with READMEs. Valid-input regression covered by the passing check targets.
- PS2-G03-2 (residual signed-overflow from huge consistent distances + missing low-side clamp in
  graphMapView2) is downstream mapping-cost code shared by all arch classes, not this group's files.

User must decide
- COR-21 A (reject, shipped) vs B (widen+clamp, alt/, not recommended); and whether to clamp
  graphMapView2's histogram low (PS2-G03-2, other area, not done here).
