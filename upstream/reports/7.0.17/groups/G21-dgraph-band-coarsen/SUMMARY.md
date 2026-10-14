# G21-dgraph-band-coarsen: summary (series based on the combined series of the 20 finished groups: base-combined = v7.0.17 + 142 commits)

DGR-07   still-present ran        medium -> patches/0001 (Ptop mirrors Coll: NULL guard, caller owns the index array) + 0002
DGR-09   still-present ran        medium -> patches/0005 (dgraphBand()/SCOTCH_dgraphBand() reworked as dgraphInduce2() 3c9b3ab: dummval, Gnum scratch, fail1/2/3) + 0011
DGR-17   still-present ran        low    -> patches/0003 (DGRAPHBANDGROWSMUL in the Coll debug bound; Ptop message name)
API-17   still-present ran        low    -> patches/0005 (same commit as DGR-09, twin copy)
API-20   still-present partly-run low    -> patches/0004 (fail1: dgraphExit of the clone, fail2: CONTEXTEXIT; SCOTCH_dgraphGrow name)
PS-DGR-5 still-present partly-run low    -> patches/0004 (duplicate of API-20)
DGR-13   still-present ran        high   -> patches/0007 (dgraphMatchSyncColl() reuses existing arrays) + 0008 (thrdtab in Init, coarse-array
                                             agreement in all build modes, adjacency result carried by the final reduction)
PS-DGR-1 still-present ran        medium -> patches/0006 (no dgraphMatchInit() after a failed dgraphCoarsenInit(); single cleanup after the agreement)
API-15   still-present ran        medium -> patches/0010 (copy only when the folded multinode array exists)
Extra: PS2-G21-1 band/grow OOM not agreed upon in release builds (hang) -> 0002; PS2-G21-2 unchecked shrinking reallocs in dgraphCoarsen() (crash,
or rc=0 with a coarse graph missing its edge loads on one process) -> 0009; PS2-G21-3 CONTEXTINIT() drops contextOptionsInit()'s result: notes only.

Series: 11 commits on base-combined (`git format-patch base-combined`), `git am` clean on a fresh v7.0.17 clone + combined series; stylecheck adds
nothing (removes two pre-existing items), `git diff --check` clean, 0 warnings on the 32-bit ASan+UBSan, 64-bit Gnum, -DSCOTCH_DEBUG_ALL and UBSan
fault-injection trees. 32- and 64-bit: all 15 CHECKPTSCOTCH targets, the dgraph test programs and dgpart/dgord/dgtst at np 1, 2, 4 and `make ptcheck`
rc=0 with ZERO sanitizer reports (chk_32/chk_64_summary.txt; the check_libparmetis_v3 rc=2 line there is my runner's link line, see the rerun line
at its end); debug tree: 9 dgraph targets rc=0. Reproducers: repro/<ID>/README, driver repro/common/g21fi.c + G18's shim, scans in repro/common/scans.

Three most important facts
1. On pristine 7.0.17, 20 of the 23 allocations of a SCOTCH_dgraphCoarsen() call hang the job when they fail on one process, and 3 crash it
   (dgraphMatchInit() on uninitialised data). After the series every one returns 2 on every rank (1 for the fold ones, G18) except the halo
   synchronization inside dgraphCoarsenBuild(), which is G20's PS-DGR-2 (dgraph_halo.c untouched). Same for every band/grow allocation: NULL
   store, invalid free of the user's part array, wrong-base free on all ranks (base 1), hang -> rc=1 everywhere, halo sync excepted.
2. Two defects nobody had listed: a failed *shrinking* realloc of the coarse edge-load array makes SCOTCH_dgraphCoarsen() return 0 with a graph
   that fails dgraphCheck ("inconsistent global graph data (2)"), and API-15 is a SEGV on every process (not just UB) whenever folding with a user
   multinode array meets a 'cannot coarsen' return (coarsening ratio not met). API-15's fix removes the last UBSan report of the combined ptcheck.
3. The maintainer's idiom was followed rather than the first pass's: dgraphInduce2()'s 3c9b3ab labels for both band builders, dgraphCoarsenBuildColl()'s
   own "TRICK: use coarse graph procrcvtab and procsndtab" for the matching arrays (no new field), dgraphGhst()'s end-of-routine agreement for the adjacency.

Could not do / residual
- dgraphHaloSync2() OOM still hangs dgraphBand(), SCOTCH_dgraphBand() and dgraphCoarsenBuild() (G20's PS-DGR-2; not patched here on purpose). The 64-bit overflow of the band scratch array and the SCOTCH_dgraphGrow() context leak are read, not observed (no 64-bit injection tree; LSan drowned by MPI).

User decisions
- Patches 0002 and 0008 perform agreements in release builds that the maintainer compiled out on purpose ("not absorbable by the algorithm"): one
  3-Gnum Allreduce per band/grow call, one int Allreduce per coarsening level. Same decision as G18/G19; 0008's other sites cost no communication.
- 0002 also makes the distance-parameter consistency check of SCOTCH_dgraphGrow() unconditional (user parameter). No regression test added
  (every defect needs a failing allocation; src/check has no fault-injection home).
