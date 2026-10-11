# Scotch v7.0.11 source analysis — synthesis

Twelve parallel analysts read the Scotch C library (~114k LOC of `libscotch`
plus the METIS/esmumps/CLI ecosystem and the `src/check` test suite),
subsystem by subsystem, in July 2026. Each wrote a standalone report (files
`01`–`12` in this directory). This is the cross-cutting synthesis.

**Ground rules the analysts worked under:** every finding must cite
`file:line` with a verbatim excerpt and a concrete failure mechanism; "no new
findings" was an acceptable result; five already-known issues (the module.h
rename-table gaps, the `contextOptionSetNum` value/index bug, the undocumented
functions) were given as calibration and excluded. Nothing here is invented —
but this is a **static read**, not proof. Findings are rated by the analyst's
confidence; only the handful marked "reproduced" were executed against the
built library. Treat the rest as high-quality leads for upstream to confirm.

Scotch is a mature, careful, 30-year-old library. The volume of findings below
is a function of how *hard* twelve agents looked at code paths that — as the
analysis itself shows — often have no test at all. Most findings are on error
paths, weighted/fixed variants, and hostile-input parsing, not the hot path.

## The two patterns that explain most findings

Nearly every memory-safety finding is an instance of one of two patterns. That
they recur across unrelated subsystems is the real result — each is a
grep-able class upstream could sweep for and a CI check could prevent.

### Pattern A — missing `return` after a failed group allocation
`memAllocGroup` returns with only its *first* pointer set to NULL on failure
(confirmed in `common_memory.c:508`). Several routines detect the failure,
run a cleanup/collective, and then **fall through into the main body** instead
of returning, operating on NULL or unallocated buffers. Seen independently in:
`library_graph_map_view.c` (report 01), `arch_*` loaders (05),
`bgraph_bipart_fm.c` (06), `dgraph_ghst.c`/`dgraph_gather_all.c` (10),
`hgraph_order_nd.c`/`hmesh_order_nd.c` (08/09). All OOM-triggered, so invisible
until memory is tight — and invisible to the default non-exiting error library.

### Pattern B — copy-paste twin divergence
Scotch is built from families of near-identical files (Init/Exit, Load/Save,
32/64, sequential/parallel, bgraph/vgraph). Repeatedly, **one twin was fixed or
written correctly and its sibling was not**. Examples: `dgraphBand` diverges
from its coarsen/induce/redist siblings in three places (02); `graphTabLoad`
mis-bases an index its `graphTabSave` twin handles right (01); `graphRemapView`
computes distance old-vs-old (01); a missing `break` leaves dead code whose
correct form exists in the sibling scan (`kgraph_cost.c` vs `kgraph_map_bd.c`,
07); `bgraph_bipart_fm.c` carries a `partval == 2` case copy-pasted from the
*separator* FM where it's meaningless (06); `bdgraph`/`vdgraph` error paths
diverge (11). A twin-diff pass over these families would surface most of them.

### The distributed corollary — deadlock on local error
The distributed reports (02, 06, 07, 10, 11) share one architectural hazard: a
rank hits a **local** fatal error (usually OOM), returns or skips a collective,
and the other ranks **block forever** on the matching `MPI_Bcast`/`Allgather`/
`Waitall`. Collective agreement on the error is only reached under
`SCOTCH_DEBUG_DGRAPH1`. This is one design pattern with many instances, not
many bugs — and it is precisely why partial failures in PT-Scotch hang rather
than report.

## Severity-ranked shortlist (the ones worth a message to upstream)

| # | Where | What | Confidence |
|---|-------|------|-----------|
| 1 | `hgraph_order_bl.c:96,192` (08) | A composed block strategy (`b{strat=f{…}}`) recurses unboundedly → **SIGSEGV**. Reachable from a user strategy string. | **reproduced** |
| 2 | `hgraph_order_cc.c:206` vs `orderCheck2` (08) | A *valid* ordering of a disconnected graph (`o{strat=s}`) is **falsely rejected** by `SCOTCH_graphOrderCheck` (DICO arity hardcoded to 2). | **reproduced** |
| 3 | `vmesh_separate_fm.c:154` (09) | Unfinished stub `fprintf(stderr,…); exit(1);` reachable from normal mesh FM refinement → **kills the host process**. | high |
| 4 | `library_dgraph_band.c:201` (02) | OOM path writes through NULL `procdsptab` → **segfault** instead of error propagation (the very path meant to propagate the error). | high |
| 5 | `graph_io_chac.c:225` (04) | Off-by-one heap write in the Chaco loader (guard `> edgenbr+1` admits index `edgenbr+1`); correct in the `graph_io.c` twin. | high |
| 6 | `bgraph_bipart_df.c:380` (06) | v7 thread-model regression (commit `67c0d61`, still in 7.0.12): anchor gain added to itself, thread reduction dead. **Reachable from default strategies**; degrades partition quality silently. | high |
| 7 | `bdgraph_bipart_sq.c:207` (11) | Checks the *local* error flag, not the reduced one → one rank returns alone, peers **deadlock**. Twin `vdgraph` does it right. | high |
| 8 | `esmumps_strat1` (12) | Emits `ole=h{…}` for HAMD, but `h` is a *separation* method (HAMD is `d`) → generated strategy **fails to parse**. One-char fix. | high |
| 9 | `graph_io_habo.c:277` (04) | Harwell-Boeing loader uses a file value directly as an array index, no range check → OOB write on malformed `.rsa`. | med |
| 10 | `library_graph_map_view.c:316` (01) | `SCOTCH_graphMapView` **destructively renumbers** the caller's `parttab` despite being a read-only "view". | med-high |

Full findings (~90 total) live in the per-subsystem reports; each has the
excerpt and mechanism. `randomVal(0)`→SIGFPE (03) is omitted here because
PyScotch already guards it — see below.

## What this means for PyScotch (actionable)

The analysis fed straight back into the bindings. Concrete items:

- **We already guard the right things.** `_wrapped_randomVal` pre-empts the
  `randomVal(0)` SIGFPE (03); our mandatory `graphCheck` after CSR import is the
  only defense against `graphBuild` storing our numpy pointers unchecked (04);
  the error-capture shim we just added exploits the same unsuffixed
  `SCOTCH_errorPrint` the rename-table analysis (03) confirms is load-bearing.
- **Validate on all ranks before every collective `Dgraph` call.** The deadlock
  corollary means a Python-side precondition check that raises on one rank hangs
  the job. Check first, collectively, then call. (02, 10, 11)
- **Harden the fixed/remap contracts.** Core code treats `>= 0` as "fixed" while
  `SCOTCH_graphRemapFixedCompute` treats `!= -1` as fixed — a `-2` silently
  corrupts (07). Our wrappers should reject anything `< -1`.
- **Weighted built meshes are hazardous:** element/node load-array conflation
  (09) makes `order()` on a `meshBuild` mesh with separate `velotab`/`vnlotab`
  read out of bounds; document the single-contiguous-load workaround.
- **Strategy strings are untrusted input.** Finding #1 is a segfault reachable
  from a strategy string; long-term we may want to reject `b{strat=…}` shapes or
  catch it. At minimum, document that arbitrary strategy strings can crash.
- **Our new `Dgraph.part()`/`order()` are the first test coverage these paths
  have ever had** (see below) — worth expanding into the untested fold-dup /
  narrow-remap / weighted cases the reports name.

Also caught in our own tree: `PORTING_STATUS.md` says "29 tests" but there are
30; `test_scotch_graph_map.c` and `test_scotch_graph_order.c` (remap, fixed
vertices, list ordering — our least-covered paths) have no Python port yet (12).

## The headline: coverage predicts bugs

The `src/check` suite is **16/30 tests return-code-only or assertion-free**
(quantified test-by-test in report 12). Bug density tracks test density almost
perfectly:

| Subsystem | Direct C tests | Findings |
|-----------|---------------|----------|
| Meshes (09) | 1 (vacuous) | ~10 |
| Bipartitioning (06) | 0 (debug-only oracle) | 11 |
| Distributed algos (11) | 0 (reached end-to-end only) | 9 |
| Seq interface map-view/IO (01) | 0 | 18 |
| Graph core (04) | good — except loaders | 3, all in the untested loaders |

The correlation *is* the argument: the findings cluster exactly where the tests
aren't. This is the strongest case for where upstream test investment pays off,
and it reframes PyScotch's own contribution — the Hypothesis suite, the
header-verified signatures, and now the first-ever harness over `dgraphPart` —
as filling precisely these gaps.

## For the conversation with the Scotch team

Bring, in priority order: **(1)** the two reproduced crashes (#1, #2) — they're
demonstrated, not theorized, and #2 is a correctness bug in a validator users
trust; **(2)** the two systemic patterns with their cross-report evidence, plus
the offer of a `library.h`-vs-`module.h` sweep and a twin-diff check as upstream
CI (both are ~15-line scripts); **(3)** the `esmumps` HAMD one-char fix (#8) as a
trivial goodwill merge; **(4)** the coverage table as the framing for "here's
where a little testing goes a long way." Everything cites file:line, so any of
it converts to a GitLab issue in minutes. The five previously-found issues and
the verified 7.0.12 build patch are in `../QUESTIONS_FOR_SCOTCH_TEAM.md` and
`../FINDINGS.md`.

## Reports

| File | Subsystem | Findings |
|------|-----------|----------|
| [01-library-interface-seq](01-library-interface-seq.md) | Sequential public API wrappers | 18 |
| [02-library-interface-par](02-library-interface-par.md) | PT-Scotch public API wrappers | ~10 |
| [03-common-infra](03-common-infra.md) | Memory, threads, PRNG, parser, naming | 6 |
| [04-graph-core](04-graph-core.md) | Graph build/coarsen/band/color/IO + ordering | 3 |
| [05-architectures](05-architectures.md) | Target-architecture family | 5 |
| [06-bipartitioning](06-bipartitioning.md) | Bgraph methods (FM, GG, diffusion, ML) | 11 |
| [07-kway-mapping](07-kway-mapping.md) | K-way, remap/repart, overlap | 5 |
| [08-separators-ordering](08-separators-ordering.md) | Vertex separators + nested dissection | 3 (2 reproduced) |
| [09-meshes](09-meshes.md) | Mesh / hmesh / vmesh | ~10 |
| [10-distributed-core](10-distributed-core.md) | Dgraph structures, fold/halo/gather | 8 |
| [11-distributed-algos](11-distributed-algos.md) | bdgraph/vdgraph/hdgraph/kdgraph | 9 |
| [12-ecosystem-tests](12-ecosystem-tests.md) | METIS/esmumps/CLI + test-suite audit | ~8 |

*Static analysis, Scotch v7.0.11, July 2026. Leads for upstream confirmation,
not verified defect reports except where marked "reproduced".*
