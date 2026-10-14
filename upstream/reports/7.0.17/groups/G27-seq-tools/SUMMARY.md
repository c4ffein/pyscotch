# G27-seq-tools -- summary (Scotch 7.0.17, sequential tools). Series is based on the combined series (tag base-combined), 11 commits.

| id | status | method | severity | patch |
|---|---|---|---|---|
| CLI-11 | still-present | ran | high | patches/0001 (graphInduceList check + archDecoArchBuild caller check), 0002 (amk_grf base + range check, test) |
| CLI-12 | still-present | ran | medium | patches/0003 |
| CLI-16 | still-present | ran | low | patches/0004 |
| CLI-17 | still-present | ran | low | patches/0005 |
| CLI-13 | still-present | ran | low | patches/0006 (+0011 style) |
| CLI-14 | still-present | ran | low | patches/0007 (gcv AND mcv) |
| CLI-18 | still-present | ran | low | patches/0008 (+4 check_prog_gmk cases) |
| PS2-G15-6 (fwd) | not-a-bug | ran | info | - (alt/PS2-G15-6-a) |
| PS2-G27-1 (new) | still-present | ran | medium | patches/0010 |
| PS2-G27-2 (new) | still-present | ran | low | patches/0009 |
| PS2-G27-3 (new) | still-present | ran | high | patches/0001 |
| PS2-G27-4..8 | info / other group | - | - | - |

Three most important facts
1. CLI-11 is high, not medium: the same unchecked vertex list reaches the public SCOTCH_archBuild0() and SCOTCH_graphInduceList()
   (heap WRITE in graph_induce.c:137), and archDecoArchBuild() ignored both graphInduceList()'s and archDecoArchBuild2()'s status
   (PS2-G27-1: returns 0 with an empty architecture). 0001 puts one unconditional check where the index array is filled
   (mirror of archDeco2ArchBuild's), 0002 fixes the tool; base-0/base-1 outputs now differ only by the label column (repro/CLI-11).
2. Differential tests for every tool are in repro/ (base-0 vs base-1 inputs, outputs identical modulo base after the fix; gmk_m2
   byte-identical to pristine for 142/150 small files, the 8 others are exactly the broken headers). CLI-17 fuzzer: 600 mutants,
   1 signature before, 0 after. All 23 relevant check targets + whole `make check` pass on 32-bit and 64-bit ASan/UBSan trees.
3. PS2-G15-6 is not a bug: all programs link libscotcherrexit, so every library errorPrint exits; orderLoad() always prints before
   returning 1 (verified by running gotst with a bad ordering: rc=1, nothing continues). No tool checks SCOTCH_graphLoad() either.
Verification: both trees 0 warnings; stylecheck flags only pre-existing lines (graph_induce.c:262, amk_grf.c:216, gcv/mcv col-49
case comments kept consistent with their file); git diff --check clean; per-commit syntax check clean; series re-applied with
git am on a fresh clone over the combined series (identical tree hash). 64-bit `make check` shows 2 UBSan lines in
mesh_induce_sepa.c:160-161 via mord (PS2-G27-7, mesh group's file), none in 32-bit.

Could not do / caveats
- No negative tests in src/check (precedent: tests must succeed); the new check lines are return-code tests, evidence is in repro/.
- Tulip ids stay based (PS2-G27-4): valid output, changing it alters existing files -- maintainer's call.
- gout man page lacks -Ov (PS2-G27-5) and check_prog_gmk's CMake twin had drifted (PS2-G27-6): not touched (G28 owns man pages).

User must decide
- CLI-11: unconditional check in graphInduceList() (shipped) vs his SCOTCH_DEBUG_LIBRARY2 habit (alt/CLI-11-c) -- see audit notes.
- CLI-16: shipped the 5-line NULL-safe-pointer variant (removes UBSan null-offset in all four writers); alt/CLI-16-a is the 1-token fix.
