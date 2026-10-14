# G28-tools-docs-tests — summary (Scotch 7.0.17; series of 8 patches ON TOP OF THE COMBINED SERIES, tag base-combined; `git am` clean on a fresh clone)

CLI-20  still-present  ran         low    -> patches/0001 (gmap.c: '(default: 0.01)', "after '-c'"; with BLD-23) + 0002 (dead '-q' check, PS2-G28-1)
CLI-21  still-present  partly-run  low    -> patches/0003 (MPI_Finalize before the 15 early returns of dggath/dgmap/dgord/dgscat/dgtst) + 0004 (MPI_Abort in libptscotcherrexit's errorPrint; h_c.tex)
BLD-23  still-present  ran         low    -> patches/0001 (gscat.c usage '-i<nbr>')
BLD-22  still-present  ran         low    -> patches/0007 (8 man sources + regenerated .1 + man/man1/Makefile -I flags + s_p.tex + p_p.tex)
BLD-18  still-present  ran         low    -> patches/0005 (CHECKSCOTCH += check_prog_atst, check_prog_mcv; atst was a second orphan)
BLD-04  still-present  ran         medium -> patches/0006 (test_scotch_graph_order: exit at the first invalid value; no more OOB read)
BLD-16  still-present  ran         medium -> patches/0008 (test_scotch_graph_map: SCOTCH_archDomTerm validity, fixed parts compared, G12's case too)
BLD-15  still-present  ran         medium -> - (fixed in the combined series by G11's 7f94e1c = work/G11-mesh-struct-io/patches/0009; proved before/after)
Extras: PS2-G28-1 dead '-q' check in gmap/dgmap -> 0002; PS2-G28-2 context leak on -h (info); PS2-G28-3 s_p.tex 'deco 0'/double -V -> 0007; PS2-G28-4 gbase/gdump have no manual section (info).

Three most important facts
1. The three test-strictness items are proved with corrupted results (repro/mutate.sh): before, all 2+1+4 corruptions pass (rc 0; BLD-04's
   out-of-range value is an ASan heap-buffer-overflow in checkOrder:103); after, every one fails (rc 1) and the unmutated tests pass on the
   32-bit and 64-bit trees. BLD-16 bounds parts by "is a terminal domain of the architecture" (SCOTCH_archDomTerm), which is right for the
   variable-sized hypercube where SCOTCH_archSize is 1 (the review's and the first pass's bounds are wrong there), and checks fixed vertices.
2. BLD-22 is wider than the three pages named: a script (repro/BLD-22/usage_vs_man.py, usage texts vs man pages vs both user's manuals, all
   36 tools) found 27 mismatches in 7 pages/sections, plus sub-flag drift, a duplicate -h, a literal \textit{nbr} and a stale 'deco 0'; after
   the patch only gbase/gdump's missing manual sections remain. The .1 pages are regenerated with txt2man exactly as man/man1/Makefile does
   (the same tool reproduces the 24 committed pages byte for byte except dates); the .1.txt sources use an ESC byte between option letter and
   argument, which the patch follows.
3. CLI-21: the help/version exits are fixed (rc 1 -> 0 for all 15 paths under mpirun). The "others hang" half could not be reproduced: Open
   MPI 5/PRRTE kills the job in < 1 s when rank 1 exits on a bad part file; patch 0004 (MPI_Abort from the PT error-exit library, guarded by
   MPI_Initialized/MPI_Finalized) makes termination launcher-independent and is a separate commit because it is a behaviour change for
   embedders of libptscotcherrexit: the user/maintainer must decide whether to keep it.

Verification: 32-bit and 64-bit ASan/UBSan trees build with 0 warnings; whole `make check` and `make ptcheck` on both trees after the
series: check32 rc=0, ptcheck32 rc=0, check64 rc=0, ptcheck64 rc=0 (logs check*.log, ptcheck*.log; only the pre-existing UBSan line mesh_induce_sepa.c:160, another group's file); atst and mcv now run (19 lines each). stylecheck.py reports only pre-existing lines (library_error_exit.c:114/166 '/*+ +*/' comments,
test_scotch_graph_order.c:89, test_scotch_graph_map.c:153); git diff --check clean.

Could not do / to decide
- CLI-21's hang needs a launcher that keeps the job alive after a non-zero exit (Slurm without KillOnBadExit); only Open MPI 5 here.
- Whether to keep 0004 (MPI_Abort in libptscotcherrexit) — recommended, separable. Alternatives: alt/CLI-21-c (usage on rank 0 only), -d (compile flag).
- gout.1 is regenerated (duplicate -h) and so carries the current txt2man's rendering of one example line (16 lines differ from the stale
  committed file, which an older txt2man produced); the maintainer's own txt2man will render it his way.
- BLD-22 touches man/man1/Makefile (-I flags) and the two manuals' program sections; the PDFs are not regenerated (release-time task).
- src/check/CMakeLists.txt needs nothing from this group (atst/mcv tests already exist there; test programs keep their arguments).
