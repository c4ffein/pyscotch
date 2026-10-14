# G10-mesh-separators — summary (8 commits on v7.0.17, all `git am` clean, 0 warnings 32/64-bit, check set green on both)

SEP-02    still-present   ran   high    -> patches/0002 (mesh_induce_sepa.c + hmesh_order_hx.c; new test_scotch_mesh_order)
SEP-15    still-present   ran   medium  -> patches/0005 (hmeshOrderNd fail label; meshInduceSepa sequential groups)
SEP-22    still-present   ran   low     -> patches/0005 + 0006 (vgraphSeparateFm fail label, Gg results in vgraph/vmesh FM)
SEP-03    still-present   ran   high    -> patches/0004 (meshCoarsen: graphCoarsen contract, matcher error, checked realloc)
SEP-18    partially-fixed ran   low     -> patches/0007 (OUCH removed, save-slot claim counts the frontier load)
PS-SEP-2  still-present   ran   medium  -> patches/0008 (vmeshSeparateFmResize completed, shield removed, save array 2*hashmax)
PS-SEP-4  still-present   ran   medium  -> patches/0003 (hall_order_hd.c nel += nv[i]; data/isolated_v.grf in gord/gotst checks)
PS2-G10-1 (new, high)      ran           -> patches/0001 (64-bit Gnum: meshInduceSepa bit array was unsigned int indexed by INTSIZEBITS)

Three facts that matter most
1. 64-bit Gnum builds (the production build) crash in default SCOTCH_meshOrder on a plain unweighted 32x32 quad mesh
   (`mmk_m2 32 32 | mord`): PS2-G10-1, not in the review, fixed by 0001 and now covered by check_prog_mmk/gmk_msh/mord.
2. SEP-02 has a second instance in hmeshOrderHxFill (HAMD/HAMF variable weights read from the element load array);
   the review's Fix line alone would have left it. PS-SEP-4 is its own halo-minimum-degree bug (zero-degree variables
   counted unweighted; HF already does it right), reachable from SCOTCH_graphOrder with d{} and from every mesh ordering
   via compression; it is not a consequence of SEP-03.
3. PS-SEP-2 was finished rather than turned into an error: the dead code had three more bugs, locked and chained elements
   were indistinguishable after re-hashing, the filling loop kept a stale node index, the save array could overflow once
   the tables fill, and the three checks placed right after a resize can never pass. Validated with a debug object that
   forces resizes (14-297 per mesh) under vmeshSeparateFmCheck; a natural pristine trigger was not found (two large
   meshes and a wedge mesh stay under the 4x shield).

Not done / limits
- No natural input reaching the pristine exit(1) of PS-SEP-2 (shield is proportional to the sweep capacity).
- hmesh_order_cp.c:209 (element load array re-used with the fine base for nodes-first meshes) is source-read only.
- Fault-injection scans show further error-path defects outside this group's files, reported in extra.json with
  compile-checked diffs: hmesh_induce.c:362 unchecked memRealloc (NULL edge array then crashes), hmesh_order_cp.c:386
  compressed ordering tree leaked, bgraph_bipart_fm.c:599 use after free on resize failure, hmesh_mesh.c message prefix.
- src/check cannot inject allocation failures: SEP-15/SEP-22 have reproducers (repro/SEP-15, repro/SEP-22), no check test.

User decisions
- 0008 removes the `/* TODO */ hashmax *= 4` shield: meshes that now resize may order differently (m2_300_300 did not
  change; ship001 slightly better). Drop that hunk if zero behaviour change is preferred (option c in audit.json).
- 0004 moves the node threshold test from vmeshSeparateMlCoarsen into meshCoarsen (same behaviour, cleaner contract).
- The new test file header says AUTHOR: PyScotch project; set the real author before sending.
