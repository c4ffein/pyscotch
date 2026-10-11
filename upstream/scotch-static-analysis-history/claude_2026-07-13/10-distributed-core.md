# Distributed core — Scotch v7.0.11

## Scope

Distributed data structures of `libscotch`, at
`external/scotch/src/libscotch/` (tag v7.0.11, read-only):

- `dgraph.c`, `dgraph_build*.c`, `dgraph_check.c`, `dgraph_coarsen.c`,
  `dgraph_compact.c`, `dgraph_fold.c`, `dgraph_fold_comm.c`,
  `dgraph_fold_dup.c`, `dgraph_gather.c`, `dgraph_gather_all.c`,
  `dgraph_ghst.c`, `dgraph_halo.c`, `dgraph_halo_fill.c`,
  `dgraph_induce.c`, `dgraph_io_load.c`, `dgraph_io_save.c`,
  `dgraph_redist.c`, `dgraph_scatter.c`, `dgraph_view.c` (29 dgraph files)
- `dorder*.c` (8), `dmapping*.c` (2), `dmesh*.c` (4)

Deep reads: `dgraph_fold*.c`, `dgraph_halo*.c`, `dgraph_ghst.c`,
`dgraph_gather*.c`, `dgraph_scatter.c`, `dgraph_redist.c`, and the
communication core of `dgraph_coarsen.c`. The dorder/dmesh/dmapping files
were swept by a subsidiary read; its two strongest findings (F7, F8) were
re-verified by hand against the source before inclusion.

## Architecture

### Dgraph distribution model

A `Dgraph` distributes vertices by contiguous global ranges per rank.
`procdsptab[p]` is the compact global start index of rank `p`;
`procvrttab[p]` is the *user-visible* global start index, which may contain
holes (`procvrttab != procdsptab` iff the graph "has holes", e.g. after
`dgraphRedist` with `vertlocdlt` slack). `vertloctax/vendloctax` are the
based local adjacency index arrays (compact iff `vendloctax ==
vertloctax + 1`; the `DGRAPHHASVENDLOC` flag marks non-compact graphs, which
`dgraphCompact2` linearizes before fold/gather). `edgeloctax` holds *global*
end-vertex indices; `edgegsttax` is the parallel array holding *local+ghost*
indices, built lazily by `dgraphGhst`.

### Ghost/halo design (`dgraph_ghst.c`, `dgraph_halo.c`, `dgraph_halo_fill.c`)

`dgraphGhst2` scans local edges, binary-searches `procvrttab` to find each
remote end's owner, sorts the remote ends (`intSort2asc1`), and assigns ghost
numbers contiguously per neighbor process in ascending global order. It also
builds `procsidtab`, a run-length-encoded "send script": negative entries are
jumps over local vertices (clamped to `DGRAPHGHSTSIDMAX` per entry so a Gnum
distance fits an int), non-negative entries name a destination neighbor.
`dgraphHaloFill` (template-expanded from `dgraph_halo_fill.c` for Gnum,
GraphPart, int, and a generic memcpy fallback) replays this script to pack
send buffers.

`dgraphHaloSync` then exchanges: either `MPI_Alltoallv` (collective mode) or
`MPI_Irecv`/`MPI_Isend` per neighbor with tag `TAGHALO` followed by one
`MPI_Waitall` (point-to-point mode). The mode is chosen once in `dgraphGhst2`
(`dgraph_ghst.c:299-304`): `DGRAPHCOMMPTOP` is set when the global neighbor
count is below `SCOTCH_COMM_PTOP_RAT` times `p*(p-1)`, overridable at compile
time by `SCOTCH_COMM_COLL`/`SCOTCH_COMM_PTOP`.

`dgraphHaloAsync`/`dgraphHaloWait` are the async path: with
`SCOTCH_MPI_ASYNC_COLL` they issue one `MPI_Ialltoallv` and stash the request
in `DgraphHaloRequest`; otherwise `dgraphHaloAsync` silently degrades to the
synchronous call and `dgraphHaloWait` just returns its stored code. The send
buffer is freed by `dgraphHaloWait`, or leaks if the caller never waits.
Note the request struct has no tag namespace of its own: only one async halo
may be in flight per communicator at a time (all use `TAGHALO`; the code base
respects this).

### Fold and fold-dup (`dgraph_fold*.c`)

`dgraphFold` splits the communicator (`MPI_Comm_split`) and calls
`dgraphFold2`, which moves all graph data from one half of the ranks onto the
other half. `dgraphFoldComm` computes the communication pattern *identically
and without communication on every rank* (inputs `proccnttab`/`procvrttab`
are replicated), starting from `DGRAPHFOLDCOMMNBR` (=2) messages per receiver
and retrying with `commmax+1` if a valid pattern cannot be built (`redo:`
loop, `dgraph_fold_comm.c:210-471`). Senders' vertex chunks are split across
receivers sorted by ascending load; a receiver in the kept half can itself
become a "sender receiver" that sheds its overload
(`DGRAPHFOLDCOMMSEND|RECV`), and small pure senders can be "interleaved" into
remaining receiver capacity. Odd process counts are handled by making part 0
the larger half (`(procglbnbr+1)/2`) and part 1 the smaller.

`dgraphFold2` exchanges seven message classes per communication
(`TAGFOLD + TAGVLBLLOCTAB/VERTLOCTAB/EDGELOCTAB/VELOLOCTAB/EDLOLOCTAB/
VNUMLOCTAB/DATALOCTAB`), with a request table laid out as
`commmax * DGRAPHFOLDTAGNBR` slots: two anonymous leading regions for
vnum/user-data messages, then per-class regions waited with `MPI_Waitany` so
index adjustment can overlap communication (`dgraph_fold.c:593-689`).
Received edge ends are renumbered via the `fldvertadjtab`/`fldvertdlttab`
binary-search accelerator. The optional `orgdataptr/flddataptr` pair folds a
user payload (the coarsening multinode array) alongside the graph.
`fldedgecnptab` duplicates `fldedgecnttab` so the MPI send buffer is never
read while in flight (`dgraph_fold.c:326-328`) — careful MPI hygiene.

`dgraphFoldDup` folds *both ways at once* (each half receives a duplicate of
the coarse graph, `pkeyglbval` = 0/1 discriminates them): threaded, it runs
the two `dgraphFold2` calls concurrently on `proccomm` and an
`MPI_Comm_dup`'d copy (needs `MPI_THREAD_MULTIPLE` on every rank, checked by
Allreduce-MIN); otherwise sequentially, part 0 then part 1.

### Gather / scatter (`dgraph_gather.c`, `dgraph_gather_all.c`, `dgraph_scatter.c`)

Root semantics are by-pointer: exactly one rank passes a non-NULL centralized
`Graph *` to `dgraphGather` (verified by an Allreduce-SUM of root flags,
`dgraph_gather.c:111-126`); *all* ranks pass non-NULL to `dgraphGatherAll`.
Both funnel into `dgraphGatherAll2` (`protnum == -1` selects
`MPI_Allgatherv`, otherwise `MPI_Gatherv`). Vertex arrays are gathered
skipping the first index (always `baseval`), then per-rank edge offsets are
re-prefixed; if `procvrttab` has holes, gathered edge ends are relabeled by
binary search into compact numbering (`dgraph_gather_all.c:418-460`).
`dgraphScatter` distributes `DATASIZE(vertglbnbr, p, i)` vertices per rank
(balanced remainder handling for non-divisible counts), scattering the
end-index per rank via a separate `MPI_Scatter` of a pre-gathered
`attrdattab` to respect the "no element read twice" rule of `MPI_Scatterv`,
then rebases local indices and calls `dgraphBuild`.

### Redistribution (`dgraph_redist.c`)

`dgraphRedist` takes a per-vertex destination array (`partloctab`), computes
per-destination counts (Allreduce-SUM), new-index permutation start offsets
(`MPI_Scan`), propagates the permutation to ghosts with `dgraphHaloSync`, and
`dgraphRedist2` packs one variable-length record per vertex (new number,
degree, old label, optional load, optional edge loads, permuted edge ends)
into a single `MPI_Alltoallv`. The destination vertex array is rebuilt
in-place using the label array as a scratch index (`TRICK` at
`dgraph_redist.c:433`), with `degrglbmax` extra slack guaranteeing the
in-place copies never overlap. Vertex labels are always created (old global
numbers if none existed).

### Dorder distributed tree (`dorder*.c`)

Each rank keeps a circular linked list of `DorderCblk` column blocks; block
identity is `(proclocnum, cblklocnum)` where `proclocnum` is the rank that
*roots* the block. Distributed blocks are created by `dorderNew` (sub-
communicator rank 0 elected owner via Allreduce); leaves carry inverse-
permutation fragments. `dorderGather` centralizes on an elected root with
`MPI_Gatherv` of leaf and tree-node records, then relinks sons into fathers;
`dorderTreeDist` rebuilds the tree on *all* ranks via `MPI_Allgatherv` plus
three sorts; `dorderPerm` produces a distributed direct permutation via
`MPI_Alltoallv`. All collective — no tags except `DORDERTAGPERI` in
`dorder_io.c`.

### Dmapping / Dmesh

`Dmapping` is a mutex-protected (`SCOTCH_PTHREAD`) linked list of mapping
fragments appended by worker threads (`dmapAdd`); `dmapSave` gathers
fragments to a root using `MPI_Recv(ANY_SOURCE, ANY_TAG)`. `Dmesh` is new in
7.0.5+ and openly experimental: the distributed dual-graph conversion
(`dmesh_dgraph.c`, 3-phase Alltoallv + hash-merge) is substantial, but the
centralized and multi-file loaders are stubs that return failure
(`dmesh_io_load.c:165`, `:396`).

## Code-quality observations

- **Error handling is "local-fatal" by design.** The recurring pattern is
  `chekglbval = cheklocval` unless `SCOTCH_DEBUG_DGRAPH1` is defined, in
  which case an extra `MPI_Allreduce` makes the error decision collective
  (`dgraph_fold.c:291-298`, `dgraph_gather_all.c:201-208`,
  `dgraph_coarsen.c:1090-1097`, `dgraph_redist.c:129-136`). In production
  builds a single-rank allocation failure returns `1` locally while peers
  enter the next collective → hang. This is a deliberate trade-off
  (comments: "Communication cannot be merged with a useful one") but it means
  *every* OOM inside a collective dgraph routine is a deadlock, not an error
  return, unless the debug layer is compiled in.
- The exception proving the rule: `dgraphGhst2` *does* pay for a dedicated
  abort collective on its OOM path (`dgraph_ghst.c:149-157`) — and then
  fumbles it (finding F1).
- MPI hygiene is otherwise good: tags are class-partitioned
  (`TAGHALO=100, TAGCOARSEN=200, TAGMATCH=300 (+1 for the reply phase),
  TAGFOLD=400 (+7 sub-tags), TAGBAND=500`, `dgraph.h:129-143`); no tag
  collisions found — per-phase single tags are safe under MPI's per-
  (source,tag,comm) non-overtaking order. Send buffers are never read while
  in flight (`fldedgecnptab` trick). Request arrays are waited completely on
  success paths.
- Reduction determinism: fold pattern computation is replicated arithmetic,
  not communication, so it is bitwise identical across ranks. Allreduces use
  MAX/SUM/MIN on ints/Gnums — no floating-point reduction-order issues in
  this territory.
- Systematic use of `restrict` and const-locals; heavy `TRICK:` comments mark
  deliberate aliasing (e.g. `senddsptab` reused as `byte**`,
  `dgraph_halo.c:123`, sized with `MAX(sizeof(int), sizeof(byte*))` at the
  allocation — correct but fragile against refactoring).
- `dgraph_redist.c` sizes all exchange counts/displacements as `int`
  (`dsnddatnbr` etc., `dgraph_redist.c:217-220`): per-rank payloads above
  2^31 Gnums overflow before `MPI_Alltoallv`. Inherent MPI-3 limitation, but
  worth knowing when redistributing very large graphs.

## Findings

### F1 — `dgraphGhst2`: missing `return` after abort collective; OOM path runs on into unallocated arrays

`dgraph_ghst.c:152-164`:

```c
  if (cheklocval != 0) {                          /* TRICK: Processes not on error will perform collective communication at end of routine */
    if (dgraphAllreduceMaxSum (reduloctab, reduglbtab, 2, 1, grafptr->proccomm) != 0) {
      errorPrint ("dgraphGhst: communication error (1)");
      return (1);
    }
  }

  vertlocmin = procvrttab[grafptr->proclocnum];
  ...
  memSet (vertsidtab,         ~0, grafptr->procglbnbr * sizeof (Gnum));
```

The design (per the TRICK comment and the matching reduce at `:290`) is: an
erroring rank performs the abort Allreduce early and bails out; healthy ranks
learn of the failure at the end-of-routine reduce. But when the early
Allreduce *succeeds*, the function does not return — it falls through and
executes the main loop with whatever failed: `vertsidtab`/`procsidtab`/
`sortloctab` unset when the `memAllocGroup` at `:141` failed (its first
pointer `procsidtab` is NULLed by `memAllocGroup`, the others are stack
garbage), or `edgegsttax == NULL` when the allocation at `:124` failed
(`memSet`/store through wild or NULL pointers at `:164`, `:188`).
Failure mechanism: OOM on any rank → undefined behavior/segfault on that rank
instead of the intended clean collective abort. Confidence: **high** that the
fall-through exists (verified against source); trigger requires allocation
failure, so operational likelihood is low.

### F2 — `dgraphGatherAll2`: error cleanup dereferences NULL `cgrfptr` on non-root ranks and reads uninitialized `recvcnttab` on the root

`dgraph_gather_all.c:209-218`:

```c
  if (chekglbval != 0) {
    if (recvcnttab != NULL)
      memFree (recvcnttab);
    if (cgrfptr->verttax != NULL) {
      if (cgrfptr->edgetax != NULL)
        memFree (cgrfptr->edgetax);               /* Arrays are not based yet */
      memFree (cgrfptr->verttax);
    }
    return (1);
  }
```

Two defects in one block: (a) `cgrfptr` may legitimately be NULL here — every
non-root rank in `dgraphGather` passes NULL — so `cgrfptr->verttax` is a NULL
dereference. Reached without debug when a non-root's own `memAllocGroup` at
`:192` fails; reached on *all* non-roots when `SCOTCH_DEBUG_DGRAPH1` is
enabled and any rank fails. (b) On the root, if the allocation at `:166` or
`:174` fails, `cheklocval=1` causes the `:191` block to be *skipped*, so
`recvcnttab` (declared `:123`, never initialized) is stack garbage; `:210`
then potentially `memFree`s a wild pointer. Confidence: **high** (code
inspection; `memAllocGroup` verified to NULL only its first argument on
failure, `common_memory.c:508-510`). Trigger: OOM.

### F3 — `dgraphFold2`: `dgraphBuild4` failure abandons outstanding MPI requests and leaks work arrays

`dgraph_fold.c:735-739`:

```c
    if (dgraphBuild4 (fldgrafptr) != 0) {
      errorPrint ("dgraphFold2: cannot build folded graph");
      dgraphExit (fldgrafptr);
      return (1);
    }
```

This return executes *before* `memFree (fldcommdattab)` (`:750`), the final
`MPI_Waitall (requnbr, requtab, ...)` (`:752`), `memFree (fldvertidxtab)`
(`:757` — the group containing `requtab` itself), and the compacted-array
free (`:758-759`). Outstanding requests in the anonymous region
(vnumloctab/user-data Irecvs on a receiver) are abandoned and their request
storage freed-by-leak; peers that sent those messages complete (sends were
matched), so this is a leak/UB (writing into `fldgrafptr` arrays freed by
`dgraphExit` while Irecvs are still active) rather than a deadlock — but the
active-Irecv-into-freed-buffer case is genuine UB. Same structural problem
in the two `SCOTCH_DEBUG_DGRAPH2` returns at `:636` and `:661` (debug
builds). Confidence: **medium-high**; trigger is `dgraphBuild4` failing
(itself only on communication error/OOM).

Related minor leak: at `:299-308` the collected-error path frees
`fldcommdattab`/`fldvertidxtab` only for receivers
(`(fldcommtypval & DGRAPHFOLDCOMMRECV) != 0`); a *pure sender* whose
folding-data `memAllocGroup` (`:281`) failed leaks the `fldcommdattab` group
allocated inside `dgraphFoldComm` (`:274`). Confidence: high, impact: leak
on OOM only.

### F4 — `dgraphFoldDup` sequential path: local failure of fold #0 skips fold #1 → peers deadlock

`dgraph_fold_dup.c:176-178`:

```c
    dgraphFoldDup2 (contptr, 0, &fldspltdat);     /* Run tasks in sequence */
    if (o == 0)
      dgraphFoldDup2 (contptr, 1, &fldspltdat);
```

Every rank participates in *both* folds (as sender in one, receiver in the
other). If fold #0 fails on one rank only (OOM; without `SCOTCH_DEBUG_DGRAPH1`
the failure is local), that rank skips fold #1 while all other ranks enter it
and post receives/sends matched against the missing rank → deadlock in
`MPI_Waitany`/`MPI_Waitall` inside `dgraphFold2`. This is the sharpest
instance of the systemic local-fatal pattern because the skip is explicit.
Also noted: `dgraph_fold_dup.c:96` `*spltptr->revaptr = 1; /* No mutex
protection */` — an acknowledged data race in the threaded path; both threads
only ever write `1`, so it is benign in practice (technically a C11 data
race). Confidence: **medium-high** for the deadlock mechanism (requires
asymmetric failure); high for the race being intentional/benign.

### F5 — `dgraphHaloSync` point-to-point error path posts sends after a failed receive; debug path leaks the comm buffer group

`dgraph_halo.c:281-307`: if an `MPI_Irecv` fails mid-loop the code breaks
with `o = 1` but then still runs the full send loop and `MPI_Waitall` on
whatever was posted. Harmless when MPI errors are fatal (default error
handler aborts), untidy under `MPI_ERRORS_RETURN`. In
`dgraphHaloSync2:238-243` (`SCOTCH_DEBUG_DGRAPH2` only), a failed
`dgraphHaloCheck` returns `1` without freeing the `memAllocGroup` buffer
allocated at `:221`. Confidence: high; impact: low (debug builds, leak
only).

### F6 — `dgraphCoarsen` intentionally desynchronizes the PRNG across ranks after fold-dup

`dgraph_coarsen.c:1475-1477`:

```c
      loopval = contextIntRandVal (contptr, finegrafptr->proclocnum + contextIntRandVal (contptr, finegrafptr->proclocnum * 2 + 1) + 1);
      while (loopval --)                          /* Desynchronize pseudo-random generator across processes */
        contextIntRandVal (contptr, 2);
```

Not a bug — it makes the duplicated halves explore different refinement
trajectories — but it is a documented-by-comment source of cross-rank RNG
divergence: after any FOLDDUP coarsening, per-rank random state differs *by
design*, so run-to-run reproducibility of parallel strategies containing
fold-dup depends on rank count and cannot be restored by a later local
re-seed alone. Confidence: high (it's explicit).

### F7 — `dorderCheck2`: `goto abort` on detected corruption abandons an in-flight `MPI_Isend` and deadlocks the ring

`dorder_check.c:188-192` (verified by hand):

```c
      if (flagloctax[perxlocnum] != ~0) {         /* If permutation index already assigned */
        errorPrint ("dorderCheck2: duplicate global %s permutation index", typestr);
        cheklocval = 1;                           /* We can exit nicely */
        goto abort;
      }
```

`abort:` (`:210`) goes straight to an `MPI_Allreduce`. The jump skips the
`MPI_Wait (&requtab[0], ...)` for the Isend posted at `:162` (request leak)
and exits the round-robin exchange early, so the peer expecting this rank's
message in a later round blocks forever in its `MPI_Wait`, never reaching the
Allreduce → deadlock — triggered precisely by the data corruption the routine
exists to report ("We can exit nicely" is optimistic). Mitigating context:
`dorderCheck` is only invoked under `SCOTCH_DEBUG_DORDER2`. Confidence:
**high** on mechanism.

### F8 — `dmeshLoadAdm`: invalid free of un-based edge array on the "bad input (2)" path

`dmesh_io_load.c:318-322` vs `:364` (verified by hand): `eelmloctax` is
allocated un-based at `:289` and only based (`eelmloctax -= baseval`) at
`:325`; the header-consistency `goto abort` at `:321` happens *before* the
basing, yet the abort path frees `eelmloctax + baseval`. For meshes with
`baseval != 0` this frees a pointer that was never returned by `memAlloc` →
heap corruption/abort on malformed input. The other `goto abort`s occur after
basing and are correct. Confidence: **high**. (Dmesh is experimental and has
no test coverage; also `dmesh_dgraph.c:592-593` calls
`dmeshDgraphDualHashEdgeResize` without checking its OOM return — and
continues inserting at a slot index probed with the *old* hash mask —
confidence medium, same experimental caveat.)

### F9 — `dgraphRedist` performs no range validation of user `partloctab`, even in debug builds

`dgraph_redist.c:145-146`:

```c
  for (vertlocnum = srcgrafptr->baseval; vertlocnum < srcgrafptr->vertlocnnd; vertlocnum ++)
    vadjloctab[srcpartloctax[vertlocnum]] ++;
```

A part value outside `[0, procglbnbr)` indexes out of bounds immediately (and
again at `:293-295`); there is no `SCOTCH_DEBUG_DGRAPH2` check anywhere in
the routine for the part array (contrast with the many internal-consistency
debug checks). Garbage-in-garbage-out is Scotch's general stance for user
arrays, but this one is a silent OOB *write*. Confidence: high on mechanism;
severity for Scotch itself: by-contract; severity for wrappers: see below.

### Lower-severity notes (verified, not elaborated)

- `dorder_io.c:178-182`: `MPI_Recv` error path leaks `permtab` (sibling path
  at `:173-177` frees it). `dmapping_io.c:277-280`: error return leaks
  `termloctab` and the committed `MPI_Datatype`.
- `dmapSave` (`dmapping_io.c:215`) drains fragments with
  `MPI_Recv(MPI_ANY_SOURCE, MPI_ANY_TAG)`: saved mapping files are correct
  but not byte-reproducible across runs.
- `dgraph_coarsen.c:1434-1436`: shrinking `memRealloc` return unchecked
  (fails only pathologically).
- No new findings in `dgraph_halo_fill.c`, `dgraph_gather.c`,
  `dgraph_scatter.c` main paths, `dgraph_fold_comm.c` pattern arithmetic
  (odd rank counts, sender-receiver overload spreading, and the interleaving
  branch all check out on inspection), or the coarsen Ptop/Coll exchanges
  (tags, request counts, and Waitall placement are correct).

## Test coverage (`src/check/`)

Seven MPI tests exist, all run on **3 ranks** (`EXECP3`) over three small
graphs (`bump.grf`, `bump_b100000.grf`, `m4x4_b1.grf` — note `_b1` gives
baseval=1 coverage):

- `test_scotch_dgraph_check.c` — dgraphLoad + dgraphCheck only.
- `test_scotch_dgraph_coarsen.c` — exercises `COARSENNONE`, `COARSENFOLD`
  *and* `COARSENFOLDDUP` on 3 ranks, so fold and fold-dup with an odd rank
  count are touched — but assertions are return-code plus a single size bound
  (`coarvertlocnbr <= coarvertlocmax`); coarse-graph *content* is never
  validated (no dgraphCheck on the result in the test itself). The test also
  calls `SCOTCH_dgraphExit` on the coarse graph when coarsening returned 1.
- `test_scotch_dgraph_band.c` / `_grow.c` — band/grow paths incl.
  `SCOTCH_dgraphGhst`.
- `test_scotch_dgraph_induce.c` — InducePart + dgraphCheck on the result.
- `test_scotch_dgraph_redist.c` — Band then Redist + dgraphCheck; only the
  internally-generated (valid) part array, zero `*dlt` slack.
- `test_scotch_dgraph_order.c` — drives dorder via OrderCompute/ComputeList +
  OrderGather (covers `dorderGather`/`dorderGatherTree`).

**Untested:** `dgraphGather`/`dgraphGatherAll`/`dgraphScatter` (only
indirectly via `dgscat`/`dggath` *programs* in `check_prog_dgscat-dggath`),
`dgraphHaloAsync` (and any `SCOTCH_MPI_ASYNC_COLL` build), `dgraphFold`'s
sender-receiver and interleaved-sender branches and the `commmax` retry loop
(3 ranks cannot reach them), fold with user payload other than the multinode
array, `dgraphRedist` with holes/slack (`vertlocdlt/edgelocdlt != 0`),
`dorderPerm`, `dorderTreeDist`, `dorderSave*`, all of Dmapping I/O, all of
Dmesh (consistent with its experimental status), and every OOM/error path
discussed above (F1-F5, F7, F8 are all in code no test reaches). Nothing
tests rank counts where fold halves differ by more than one, or ≥4 ranks at
all.

## PyScotch relevance

- **Collective contracts.** Every routine PyScotch wraps here is collective
  over `proccomm`: Build, Check (ring + per-round Allreduce), Ghst, Coarsen,
  Fold (implicit in coarsen flags), Gather/GatherAll, Scatter, Redist,
  InducePart, Band/Grow, and even a first call to any halo-using routine
  (lazy `dgraphGhst`). The shim must guarantee all ranks enter the same call
  in the same order; per F4/systemic pattern, a Python-side exception on one
  rank between paired calls will hang the others, so wrap per-rank failure
  checks in an explicit user-level Allreduce before proceeding.
- **Root semantics.** `SCOTCH_dgraphGather`: exactly one rank passes non-NULL
  `cgrfptr` (enforced by Allreduce, error otherwise); `dgraphGatherAll`: all
  ranks non-NULL. `dgraphScatter`: exactly one rank passes the centralized
  graph. Passing NULL on all ranks is caught; passing two roots is caught;
  but per F2, an OOM during gather on a non-root is a segfault, not an error
  code.
- **Pointer retention.** `SCOTCH_dgraphBuild` does **not** copy: the Dgraph
  keeps raw pointers into the user's vertloctab/vendloctab/velotab/edgetab/
  edlotab arrays for its whole lifetime (`dgraphBuild2` stores them
  directly). ctypes buffers must be kept alive until `dgraphExit`, and must
  not be resized/moved (no NumPy reallocation). By contrast Scatter, Redist,
  Gather and Fold allocate their own output arrays inside the library
  (`DGRAPHFREETABS` set), so output object lifetimes are Scotch-managed.
- **proccomm assumptions.** `dgraphInit` stores the communicator as-is
  (freed only if `DGRAPHFREECOMM`, which user-built graphs don't set); fold
  and fold-dup create sub/dup communicators internally and free them via
  graph flags. The custom MPI shim must therefore support `MPI_Comm_split`,
  `MPI_Comm_dup`, `MPI_Ialltoallv` (only if built with
  `SCOTCH_MPI_ASYNC_COLL` — safer to build without), `MPI_Scan`,
  `MPI_Type_contiguous/commit/free` (coarsen multinode payload),
  `MPI_Type_get_extent`, and correct `MPI_Get_count` on Gnum types. Halo
  paths switch between Alltoallv and Isend/Irecv at runtime based on
  `SCOTCH_COMM_PTOP_RAT` — both must work; forcing one via `SCOTCH_COMM_COLL`
  at build time reduces shim surface.
- **Redist input validation (F9).** PyScotch should validate
  `0 <= partloctab[i] < procglbnbr` on the Python side before calling
  `SCOTCH_dgraphRedist`; Scotch will OOB-write on bad values even in debug
  builds. Same argument for `vertlocdlt/edgelocdlt >= 0`.
- **Reproducibility.** Beyond `SCOTCH_randomReset` (already documented),
  fold-dup coarsening desynchronizes the PRNG across ranks *by design* (F6):
  bit-identical repeatability of strategies containing fold-dup requires
  identical rank counts and identical initial seeds, and results will still
  differ from non-folded runs. Also `dmapSave` output line order is
  arrival-order nondeterministic — don't diff mapping files byte-wise across
  runs.
- The "coarsen returns 1 leaves coarse graph invalid" behavior is already
  documented in the project; note only that upstream's own
  `test_scotch_dgraph_coarsen.c` nevertheless calls `SCOTCH_dgraphExit` on
  that invalid graph (works because the struct was zeroed on entry for the
  fold path and Exit tolerates it in the non-fold path) — this is worth a
  question to the Scotch team rather than a behavior to imitate blindly.
