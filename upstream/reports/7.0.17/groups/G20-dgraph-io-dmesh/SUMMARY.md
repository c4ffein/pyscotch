# G20-dgraph-io-dmesh: second-pass summary
DGR-03 still-present ran high -> 0001+0002 | DGR-19 still-present ran low -> 0003
DGR-15 still-present ran low -> 0004 | DGR-20 still-present ran low -> 0005
CLI-04 still-present ran medium -> 0006 | DGR-16 not-a-bug ran info -> 0007 (latent-safety; branch unreachable)
PS-DGR-2 still-present ran medium -> - (design decision; alt A tested)
PS2-G20-1 (new) ran high -> 0001/0002 (negative counts: huge alloc + np>=2 hang)
PS2-G20-2 (new) ran medium -> - (dgraphSave local-alloc hang; sibling of PS-DGR-2)

7 commits on v7.0.17; `git am` clean on a fresh clone; stylecheck adds nothing over pristine on every
touched file; diff --check clean; 0 warnings in 32- and 64-bit Gnum trees; each reproducer fails pristine,
passes patched. All PT-Scotch check targets touching these files pass rc=0 on 32- and 64-bit (dgraph_{check,
band,grow,redist,induce,order,coarsen}, prog_{dgtst,dgord,dgpart,dgscat-dggath}, libparmetis_v3,
libparmetis_dual); only sanitizer notes are pre-existing UBSan in bgraph_bipart_ml.c (G08), on pristine too.

Three most important facts
1. DGR-03 (worst): SCOTCH_dgraphLoad on a property value outside 0..111 overflows a 4-byte stack buffer on
   EVERY rank (the error flag was set on a variable never broadcast); newly, a negative vertex/edge count
   causes a near-SIZE_MAX memAlloc and an np>=2 deadlock. 0001 fixes propagation+counts; 0002 makes both
   distributed loaders faithful twins of graphLoad (labels/degrees/edge-loads/unlabeled edge-end range),
   per the forwarded G14 lead.
2. DGR-19 is reachable and worse than "leak": after a receiver's edge-array OOM, the root leaves an
   unmatched abortion message that HANGS the communicator's next collective (shown by a second load); 0003
   waits on pending sends and skips the refusing rank.
3. DGR-16 confirmed not-a-bug ('bad input (2)' unreachable behind the header-sum check, verified np=1/np=2);
   0007 is only the maintainer-suggested latent-safety hardening.

Could not do / residual
- The dgload mutation fuzzer reproduced nothing pristine or patched (mutation distribution + mpirun/ASan
  capture); crafted reproducers + fault injection are the evidence, not fuzz counts.
- CLI-04's CMake link line verified by inspection vs the Makefile and every sibling tool; no full CMake
  build run (sanitizer tree is Makefile-based); the functional adm2dgr run used the exit library.

User / maintainer must decide
- PS-DGR-2 (+ sibling PS2-G20-2, and DGR-20's multi-process returns): halo collective-safety is a design
  choice. alt A (unconditional Allreduce in dgraphHaloSync2) is tested and removes the hang but adds a
  collective to a hot path inside diffusion loops; alt B (pre-allocate scratch at dgraphGhst time, zero
  per-call cost) is preferred but touches G19's dgraph_ghst.c and the Dgraph struct. No patch committed.
- Forwarded lead (b) dmapSave NULL-parttab (first pass's PS2-G05): guard in alt/PS2-G05-...diff; real fix
  belongs in the distributed mapper. DGR-16's 0007 may be dropped if unreachable paths are left untouched.
