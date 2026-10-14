# G24-hdgraph: summary (second pass; series based on the combined series of the 20 finished groups PLUS G23's 11 patches = tag base-g23)

DMO-01    fixed-in-7.0.17  ran        high   -> - (4ebcc6f verified: np 3/5 weighted ordering valid; reverted build reproduces ASan overflow / MPI_ERR_TRUNCATE)
DMO-16    partially-fixed  ran        low    -> patches/0003 (nested dissection folded graphs), 0004 (recursive bipartitioning); fold part covered by G18 7018b17
PS-DMO-4  fixed-in-7.0.17  ran        medium -> - (covered by G18 7018b17: every fold allocation failure returns 1 everywhere; pristine hangs)
DMO-06    still-present    ran        medium -> patches/0002 (leaf statuses returned; Si2/Sq/Nd2/Nd agree)
DMO-07    still-present    ran        medium -> patches/0001
DMO-08    fixed-in-7.0.17  ran        medium -> - (covered by G18 81b8fbc; pristine SEGV on root allocations (1)-(3) under pattern init, base clean)
PS-DMO-5  still-present    partly-run low    -> patches/0002 (MPI_Bcast of the root status)
DMO-17    not-a-bug        ran        info   -> patches/0007 (docs: p_l.tex stale "6.0 ... next release", dgmap.1 'wcmplt')
PS2-G18-1 still-present    ran        medium -> patches/0005 (+ sequential twin hgraph_induce.c, kdgraph domain array = G23's PS2-G23-4)
PS2-G18-3 still-present    ran        medium -> patches/0002
DMO-18    partially-fixed  partly-run info   -> patches/0006 (|| in 4 dispatchers); hdgraph_fold.c instance covered by G18 7018b17
Extra: PS2-G24-5 (leaf failures of parallel recursive bipartitioning hang the others) -> patches/0008; PS2-G24-1 (API-level local failures hang,
library_dgraph_order.c), PS2-G24-2 (dgmap cannot read a centralized target file with np >= 2; no check_prog_dgmap), PS2-G24-3 (dorderSave waits
forever on an incomplete ordering), PS2-G24-4 (remaining hangs: vdgraphGatherAll, dgraphHaloSync2): notes only (other groups' files).

Series: 8 commits on base-g23 (base-combined + G23; G23's 0010 touches kdgraph_map_rb_part.c, cherry-picked cleanly on top of it), `git am` clean
on a fresh clone (v7.0.17 + combined + G23 + these), stylecheck adds nothing (8 pre-existing hits), `git diff --check` clean, 0 warnings on the
32-bit ASan, 64-bit and -DSCOTCH_DEBUG_ALL trees. check_scotch_dgraph_order, check_scotch_dgraph_check, check_prog_dgord, check_prog_dgpart at np 1, 2, 3, 4 (dgord/dgpart rc=2 at np != 4 only on the
Makefile's 4-process distributed-file line) and the whole `make ptcheck` pass on the 32-bit and 64-bit trees (chk_32/, chk_64/; the 3 UBSan lines
of ptcheck are the pre-existing library_dgraph_coarsen.c:163); the -DSCOTCH_DEBUG_ALL tree passes the dgraph order/check/induce/redist and dgord/dgpart
targets; the sequential twins check_scotch_graph_induce/graph_order and check_prog_gord pass on the 32-bit tree. Gathered orderings validated with
SCOTCH_graphOrderCheck at np 1..5 on m16x16 and a vertex-weighted 4elt, 32- and 64-bit (repro/common/check_mode_final.txt).

Three most important facts
1. On the base, every out-of-memory inside the parallel ordering path that belongs to these files either crashed every process (dorderNew NULL,
   NULL edge array after a failed shrink: 6 points), hung the other processes (hdgraphOrderNd2/hdgraphOrderSi2 release-only agreements: 33 points
   on rank 0) or left the processes disagreeing (every failure after the fold: ranks of the failed half return 1, the other half 0, so a user
   who tests the status before the next collective hangs). After patches/0001-0005 every such point returns 1 on every process with 0 leaked
   blocks (live-block counting shim, baseline 0); the same design (final agreement) applied to parallel mapping (0008).
2. Four review/first-pass items were already fixed in the combined base by G18 (DMO-08, PS-DMO-4, the fold part of DMO-16, the hdgraph_fold.c
   instance of DMO-18): verified at runtime against pristine 7.0.17 (pattern-init SEGV / hangs) and not re-patched.
3. The folded-graph leaks are bigger than the review's list: when one of the two parts fails after the other was folded, every receiver of the
   successful part leaked its whole folded graph (nested dissection and recursive bipartitioning); fixed with a per-part status in both Fold
   routines (also in the threaded variant).

Could not do / residual
- No regression test added: every defect needs an injected allocation failure, which src/check cannot do; the PT-Scotch check targets were run instead.
- Remaining hangs on the same paths are in other groups' files (strategy parser/context init at API level, vdgraphGatherAll, dgraphHaloSync2,
  bdgraphGatherAll/dgraphGatherAll2 on the mapping path): recorded in extra.json, not patched.
- Index-based injection scans were made with MPI_Init drivers (deterministic); the key readings were redone with MPI_Init_thread(MULTIPLE)
  drivers and per-routine injection (repro/common/reverify_thread.txt). All classes were confirmed (HANG/CRASH/DISAGREE/LEAK on the base, rc=1 everywhere and 0 live blocks
  patched; no-injection runs never hang with either driver).

User decisions
- patches/0002 and 0008 add unconditional agreements (one Allreduce per hdgraphOrderSi2 leaf, one Bcast per sequential leaf, one Allreduce per
  nested dissection / recursive bipartitioning call) in release builds, like G18/G19: the maintainer's "communication cannot be merged with a
  useful one" release-mode choice is reversed; the alternative (agree once in the API routines, alt/PS2-G18-3-B) keeps the hangs.
- DMO-17: documentation-only fix committed; alt/DMO-17-C (reject non-complete targets in SCOTCH_dgraphMapCompute) is the behavioural option.
