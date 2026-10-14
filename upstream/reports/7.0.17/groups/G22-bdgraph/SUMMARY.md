# G22-bdgraph: summary (series based on the combined series: base-combined = v7.0.17 + the 142 patches of the 20 finished groups)

DMO-09   still-present   ran        medium -> patches/0004 (bal recomputed in Zero, Sq, MlUncoarsen, GatherAll's Bgraph; divergence across folded halves reproduced)
DMO-11   still-present   partly-run low    -> patches/0005 (ABS at the two producer sites; vdgraph twins for G23 in alt/DMO-11-twin-*.diff)
DMO-18   partially-fixed ran        info   -> patches/0006 (default case unconditional, as the vdgraph twin; hdgraph_fold.c half fixed by G18; sibling diffs for G23/G24 in alt/)
DMO-19   still-present   ran        info   -> patches/0007 (ex accounting, gather veex before early return) + 0008 (exchange-based coarse merge, uncoarsening part-0 gains)
DMO-03   still-present   ran        high   -> patches/0001 (+ 0002 bdgraphGatherAll agreement, PS2-G22-1), tolerate partial sequential failures as the vdgraph twin
DMO-10   fixed-in-7.0.17 ran        low    -> - (f545452 complete for the library; two Anum abs() left in test/tool files: extra PS2-G22-6)
PS-DMO-3 fixed (combined 0074, G13) ran low -> - (flag macros unsigned; no shift report in any band run)
Extras: PS2-G22-1 (gather not collective) -> 0002; PS2-G22-2 (veextax never gathered) -> 0007; PS2-G22-3 (uncoarsen part-0 gains) -> 0008; PS2-G22-4/5/6 (vdgraphCheck names, dgmap np>=2, Anum abs) notes and alt diff.

Series: 8 commits on base-combined; `git am` of combined series + patches/ clean on a fresh v7.0.17 clone; `git diff --check` clean; stylecheck
adds nothing (10 pre-existing hits remain, 3 removed); 0 warnings on the 32-bit ASan, 64-bit, UBSan/pattern-init and -DSCOTCH_DEBUG_ALL trees;
all 14 CHECKPTSCOTCH targets pass on 32-bit and 64-bit (ptcheck_32.txt, ptcheck_64.txt; only expected negative-test messages and the known
library_dgraph_coarsen.c:163 UBSan hit), 6 dgraph targets pass on DEBUG_ALL (ptcheck_dbg.txt); dgpart/dgord -np 1..4 on 32/64-bit clean
(repro/tools_np_runs.txt). dgmap is not in CHECKPTSCOTCH (no check_prog_dgmap target exists) and fails at np>=2 on base too (PS2-G22-5).

Three most important facts
1. DMO-03 is the default-strategy hang: with q{strat=...} (coarsest levels of SCOTCH_dgraphMap/Part), a sequential OOM on one process made
   that process return 'internal error' alone while the others waited in MPI_Bcast, and a part-array OOM scattered into NULL (SIGSEGV); the
   gather two allocations earlier aborted the job in MPI. After 0001+0002 every injected failure returns 1 on all processes, and a process
   whose sequential bipartitioning failed takes the best partition of another one (what the reduction operator was written for).
2. DMO-09 is real and worse than 'Low': with duplicated folding (the default) processes of different halves hold different 'bal' values for
   the same partition (rank 0: 0.000128, rank 1: 0 at np=2), the coarse value is never initialised at all, and the gathered Bgraph's bbalval
   is uninitialised on every Sq but the first, so a '(bal<0)?z;' sequential sub-strategy ran z on pattern-initialised garbage.
3. The external-gain path (DMO-19) was broken in four places, not two: besides the merge indices and the doubled exactifier term, the gathered
   veextax was never filled (sequential methods computed on 0xBEBEBEBE) and the uncoarsening dropped the gain of received part-0 vertices.
   All four are fixed and exercised end to end by repro/common/bipartfi.c (veex=1) with bdgraphCheck on release and DEBUG_ALL trees.

Could not do / residual
- DMO-11's tie-break effect was not provoked at runtime (needs two processes with equal cut and opposite-sign imbalance in one reduction).
- No src/check test added: none of the defects is reachable through the public API without fault injection or an external gain array; the
  driver + LD_PRELOAD harness under repro/common is the regression test.
- Other groups' files untouched: vdgraph twins (G23), order_st '&&' (G24) are alt diffs; dgraphHaloSync2 OOM still hangs in the scans (G18 noted).

User decisions
- Patch 0008 (exchange-based coarse external-gain merge, ~200 lines in a path production cannot reach yet): merge now, or hold until bdgraphInit
  computes external gains (alt/DMO-19-B-refuse-external-gains-in-coarsening.diff is the fail-loudly alternative; 0007 stands alone).
- Patch 0001: release behaviour on partial sequential failure becomes tolerance (vdgraph twin semantics); alt/DMO-03-B keeps the hard check.
- Patch 0002 adds one unconditional MPI_Allreduce per bdgraphGatherAll call in release builds (his own hdgraphGather() 2026 idiom).
