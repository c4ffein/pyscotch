# Ecosystem & test suite — Scotch v7.0.11

## Scope

Reviewed at tag v7.0.11 (read-only submodule `external/scotch`):

- `src/libscotchmetis/` — METIS v3/v5 and ParMETIS v3 API emulation (23 C files).
- `src/esmumps/` — MUMPS ordering interface (symbolic factorization, `esmumps()` entry).
- `src/scotch/` — CLI programs (gpart/gmap, gord, gout, gtst, amk_*, gmk_*, dg* …).
- `src/check/` — the C test suite: 30 `.c` test programs plus one Fortran template
  (`test_libmetis_dual_f.f90.in`), driven by `src/check/CMakeLists.txt`.

Headline section is the test-suite assessment (test-by-test classification of what is
actually asserted). Known findings from other analysts (rename table, `contextOptionSetNum`,
undocumented functions) are excluded per calibration.

## Architecture

### METIS compatibility layer (`libscotchmetis`)

**Dual-version scheme.** `library_metis.h:211-229`: internal `METIS_V3_*` and `METIS_V5_*`
symbols are always compiled; the public unversioned names (`METIS_NodeND`,
`METIS_PartGraphKway`, …) are thin stubs selected by `SCOTCH_METIS_VERSION` (default 3).
One compiled library exposes exactly one public METIS ABI. ParMETIS mirrors this with
`SCOTCH_PARMETIS_VERSION` (`library_parmetis.h:160-169`).

**Entry points provided:** v3 `METIS_PartGraphKway/Recursive/VKway`, `METIS_EdgeND/NodeND/NodeWND`;
v5 `METIS_PartGraphKway/Recursive`, `METIS_NodeND`, `METIS_SetDefaultOptions`,
`METIS_MeshToDual`, `METIS_PartMeshDual`; ParMETIS `V3_PartKway`, `V3_PartGeomKway`,
`V3_NodeND`, `V3_Mesh2Dual`. **Not provided:** `METIS_Free` (yet `METIS_MeshToDual`
returns `malloc`'d arrays, `metis_graph_dual.c:246-247` — code calling real `METIS_Free`
won't link), `METIS_MeshToNodal`, `METIS_PartMeshNodal`, `METIS_ComputeVertexSeparator`,
`METIS_NodeNDP`, and the v4 `METIS_WPartGraph*` / `METIS_mCPartGraph*` families.

**Semantic gaps vs real METIS** (each verified in source by a subagent; spot-checks by me):

- `options[]` is almost entirely decorative. `METIS_SetDefaultOptions` zeroes the array
  (`metis_options.c:66-74`); the only slots ever read are `METIS_OPTION_NUMBERING`
  (v5 baseval) and `METIS_OPTION_OBJTYPE` (only in `METIS_PartMeshDual`,
  `metis_graph_part_dual.c:217`). SEED, NITER, UFACTOR, CONTIG, MINCONN, DBGLVL, etc. are
  silently ignored. Requesting `METIS_OBJTYPE_VOL` on `METIS_PartGraphKway` still returns
  the cut (volume is computed only when `vsize != NULL`).
- `EdgeND` and `NodeND` are literally the same algorithm — both funnel into the static
  worker `_SCOTCH_METIS_Node` (`metis_graph_order.c:72,129,146`); the edge/node objective
  distinction is not honored.
- **Multi-constraint (`ncon > 1`) is silently broken:** `ncon` only strides `tpwgts`
  (`metis_graph_part.c:274-275` `twdbtab[i] = tpwgts[i * *ncon];`); the interleaved
  length-`ncon*n` `vwgt` is passed to `SCOTCH_graphBuild` as a length-`n` single-weight
  array, so vertex loads become a meaningless mix. Only `ubvec[0]` is honored (passed as
  scalar `kbalval`, dereferenced at `metis_graph_part.c:290`).
- `vwgt`/`adjwgt` for `ncon==1` and `tpwgts` (via `SCOTCH_archCmpltw`) are honored.
  `edgecut`/`objval` is **genuinely recomputed** by walking the graph
  (`_SCOTCH_METIS_OutputCut`, `metis_graph_part.c:108-127`), not faked; `-1` on failure.
- `perm`/`iperm` are deliberately swapped when handed to Scotch
  (`metis_graph_order.c:101` — "MeTiS and Scotch have opposite definitions for (inverse)
  permutations"). Correct, but the single most common porting trap for callers and tests.
- numflag/baseval: inputs are never shifted in place (based "tax" pointers by subtraction);
  the only in-place mutation is re-basing the output `part` array
  (`metis_graph_part.c:318-323`). Arbitrary self-consistent baseval works in the
  part/order paths.
- ParMETIS: `ncon`, `ubvec`, `options` explicitly ignored (`parmetis_dgraph_part.c:130-134`);
  `V3_PartGeomKway` discards `ndims`/`xyz` and forwards to PartKway. `edgecut` comes from
  the dgraphMapStat distance histogram (`*edgecut = cdsttab[1];`, line 192). `tpwgts` is
  dereferenced unconditionally (line 156) — NULL crashes (real ParMETIS also requires it).

### esmumps (MUMPS interface)

`esmumps()`/`esmumpsv()` (`library_esmumps.c:71,90`) forward to `esmumps2()`
(`esmumps.c:106`); `esmumpsv` supplies `nvtab` as vertex weights, `esmumps` passes NULL.
The pipeline: build a base-1 Scotch `Graph` (`graphBuildGraph2`) → `orderGraph()`
nested-dissection ordering → `symbolFaxGraph()` block symbolic factorization → a loop
(`esmumps.c:198-228`) that writes results back into the caller's MUMPS arrays:
`nvtab` = block degree for principal variables / 0 for secondary; `petab` = elimination
tree links (0 = subtree root, else father node or negated principal variable). The
`elentab`/`lasttab` permutation arrays are documented as outputs but written **only** under
`#ifdef ESMUMPS_DEBUG` (`esmumps.c:165-168`) — a production build leaves them untouched
despite the header comment (documentation/behavior mismatch, medium).

The strategy actually used by `orderGraph` is hardcoded and correct
(`order_scotch_graph.c:113`, `ole=f{...}/ose=g`). The separate public
`esmumps_strat1` builder (`library_esmumps_strats.c`, MUMPS-facing only) contains the
HAMD strategy bug — see F5.

### CLI programs (`src/scotch/`)

Shared CLI helpers live in libscotch `common.c`/`common_file.c` (`fileBlock*`,
`errorPrint`, `usagePrint`, `memAllocGroup`). CLI mains link `libscotcherrexit`, whose
`errorPrint` calls `exit(EXIT_FAILURE)`, so every `errorPrint` is fatal (the gout
option-error paths below are therefore not fall-through bugs). **`gpart` is `gmap.c`
compiled with `-DSCOTCH_COMPILE_PART`** (`gmap.c:177-184`); likewise **`dgpart` is
`dgmap.c`**. `gout` is split into `gout_c.c` (control/loading/option parsing) and
`gout_o.c` (PostScript/OpenGL/Tulip renderers). `gord` orders; `gotst` (`gotst.c`) loads
graph+ordering, runs `SCOTCH_graphOrderCheck`, then `factorView` reconstructs the
elimination tree and computes NNZ/OPC/height statistics — a CLI-only reimplementation of
what esmumps `symbol_cost.c` does.

**Library paths exercised only through the CLIs** (from `src/check/CMakeLists.txt` and
program sources — no `src/check` test touches them):

- Geometry handling: `SCOTCH_graphGeomLoad*`/`SCOTCH_geom*` — only via `gout` (and `gcv`,
  which has **no test at all**, not even a CLI smoke test; only the mesh converter `mcv`
  is tested).
- Target-architecture builders `amk_ccc/fft2/hy/m2/p2/grf` and decomposition compiler
  `acpl` — CLI-only, and only `amk_m2 | acpl | atst` (`CMakeLists.txt:433`) actually
  validates output; the other `amk_*` tests write to `/dev/null` (return-code only).
- Sequential k-way `SCOTCH_graphPart`/`SCOTCH_graphMap` end-to-end with target files —
  via `gpart`/`gmap` + `gmtst`; distributed partitioning `SCOTCH_dgraphPart/dgraphMap`
  has **no `src/check` test at all** — only the `dgpart` CTest invocations.
- Mesh ordering `SCOTCH_meshOrder` — only via `mord` (piped into `gotst`).
- `gdump` (graph-to-C-code) — exercised as the *generator* for `test_scotch_graph_dump`.
- Ordering statistics/tree analysis — only via `gotst`.

## Code-quality observations

- The check suite relies heavily on the CTest harness for validation: the strongest tests
  are the ones whose C code asserts nothing but whose CTest entry pipes output through
  `cmake -E compare_files` against golden files (`gbase`, `gtst` ev/elv equivalence,
  `dgscat|dggath` roundtrip, `gmk_msh -d`, `mcv`, `adm2dgr`, `test_scotch_graph_dump`,
  `test_common_file_compress`). Reading only the `.c` files understates the suite; reading
  only CMakeLists overstates it.
- Repeated copy-paste error-message labels (`"out of memory (1)"` twice in
  `test_scotch_graph_color.c:162,167`; `"out of memory (3)"` twice in
  `test_scotch_graph_coarsen.c:314,334`) — harmless but shows the tests get little review.
- Output-routine return values are routinely ignored in tests
  (`SCOTCH_graphOrderSave*` at `test_scotch_graph_order.c:147-149`, `SCOTCH_graphMapSave`
  at `test_scotch_graph_map.c:234`), so save-path regressions are invisible.
- `test_scotch_dgraph_coarsen.c:216,236` calls `SCOTCH_dgraphData` and `SCOTCH_dgraphExit`
  on the coarse graph even when `SCOTCH_dgraphCoarsen` returned 1 ("could not coarsen").
  This repo's own CLAUDE.md guidance (derived from PyScotch experience) says the coarse
  graph is invalid in that case and must not be exited. Either the guidance is overly
  conservative for v7.0.11 or the upstream test relies on undefined behavior — worth a
  question to upstream.
- METIS v3/v5 test coverage exists (`test_libmetisv3/v5` built from one source), but the
  v5 test always passes a non-NULL `kbaltab`, which is exactly why Finding F1 below
  survives (the NULL-`ubvec` path is never executed by the suite).

## Findings

New findings only; file:line, excerpt, mechanism, confidence.

**F1 — NULL-pointer dereference: v5 `METIS_PartGraphRecursive` with `ubvec == NULL`
(high confidence; verified directly).**
`metis_graph_part.c:592` (and 595 for the vsize path):

```c
          ? _SCOTCH_METIS_PartGraph (nvtxs, ncon, xadj, adjncy, vwgt, adjwgt,
                                     &baseval, nparts, tpwgts, options, objval, part,
                                     SCOTCH_STRATRECURSIVE, ubvec)
```

The sibling `METIS_V5_PartGraphKway` (lines 553-562) guards with
`(ubvec != NULL) ? ubvec : &kbalval` (`kbalval = 0.01`); Recursive passes `ubvec` bare.
Downstream it is dereferenced unconditionally: `metis_graph_part.c:290`
`SCOTCH_stratGraphMapBuild (&stradat, flagval, *nparts, *kbalval);`.
Real METIS v5 documents `ubvec = NULL` as "use default" — a fully legal call crashes.
Never caught because `test_libmetis.c:100` always passes `kbaltab`.

**F2 — invalid pointer arithmetic on NULL `vsize`, `METIS_PartMeshDual` volume path
(medium confidence).**
`metis_graph_part_dual.c:216-221`: when `options[METIS_OPTION_OBJTYPE] == METIS_OBJTYPE_VOL`
but `vsize == NULL`, the call computes `vsize - baseval`. With `NUMBERING = 1`,
`NULL - 1` is non-NULL, so `_SCOTCH_METIS_OutputVol`'s `if (vsiztax != NULL)` guard
(line ~170) passes and `vsiztax[vertnum]` is an out-of-bounds read. Requires the specific
combination numbering=1 + OBJTYPE_VOL + vsize=NULL.

**F3 — `ParMETIS_V3_NodeND` returns `METIS_ERROR` despite computing a valid ordering on
non-power-of-2 communicators (medium confidence).**
`parmetis_dgraph_order.c:122,151,209`: the return value `o` starts at `METIS_ERROR` and
is set to `METIS_OK` only inside the `bitsnbr == 1` (power-of-2 npes) branch that builds
`sizes`; yet `order` is filled unconditionally via `SCOTCH_dgraphOrderPerm` (line 151).
Callers on 3/5/6/... ranks get a correct permutation plus an error code and `sizes` full
of `~0`. Surprising even if ParMETIS documents separator trees for power-of-2 npes only.

**F4 — `*objval` left uninitialized on error in the volume path (low confidence /
low impact).** `metis_graph_part.c:397,407,431`: `_SCOTCH_METIS_PartGraph_Volume` returns
`METIS_ERROR` without writing `*volume`, whereas the cut path sets `*edgecut = -1`
(line 351). Callers that check objval instead of the return code read garbage.

**F5 — `esmumps_strat1` emits an invalid ordering strategy for HAMD (high confidence;
verified directly).** `library_esmumps_strats.c:104`:

```c
hamxval = (leorval == 0) ? 'h' : 'f';           /* HAMD if 0, HAMF if 1 */
```

`hamxval` is substituted into `...,ole=%c{cmin=...}` (line 126). But the graph-ordering
method table (`hgraph_order_st.c:135`) registers HAMD under letter `"d"`, not `"h"`
(`"h"` is a *separation* method — greedy graph-growing — not an ordering method). So when
HAMD is requested (`leorval == 0`) the generated strategy contains `ole=h{...}`, which
`SCOTCH_stratGraphOrder` rejects as an unknown method → the whole strategy fails to parse.
`leorval == 1` (`'f'`, HAMF) is correct. `esmumps_strat1` is a public MUMPS-facing entry
(`library.h`) not called inside Scotch, so the defect is latent within this tree — but any
MUMPS build requesting HAMD via this helper gets a parse failure.

**F6 — `gout` NULL-deref on malformed `-O` option string (medium-high confidence;
verified directly).** `gout_c.c:708-709`:

```c
argeptr = strpbrk (argbptr, ",}\0");        /* Search for the argument end  */
if (*argeptr == '\0')                       /* If there is no end delimiter */
  return (3);                               /* Return syntax error value    */
```

The accept-set string `",}\0"` is a C string literal, so `strpbrk`'s effective accept set
is just `{',', '}'}` — the embedded `\0` is the terminator and is never a searchable
character. The intended "detect end of string" therefore cannot fire: an `-O` value that
opens `{` but reaches end-of-string with no `,`/`}` (e.g. `-Ov{color`) makes `strpbrk`
return NULL, and line 709 dereferences NULL → segfault instead of returning syntax-error 3.
The bounded copy immediately after (`argubuf[128]`, capped 127, explicit NUL) is correct.

**F7 — unchecked returns in the `esmumps2` pipeline (medium confidence).**
`esmumps.c:143,171`: the return codes of `orderGraph` and `symbolFaxGraph` are ignored.
On ordering failure `orderGraphListStrat` frees and re-inits to an empty order
(`order_scotch_graph.c:186-190`); `symbolFaxGraph` then runs on the empty ordering and the
block-walk (`esmumps.c:198-228`) dereferences `peritax`/`cblktax` for a zero-block order →
garbage writes or crash. Also a conditional leak (`esmumps.c:153-156`, `ESMUMPS_ORDER_DUMP`
only): `return 1` on `fopen` failure without freeing `vendtab`/order/graph.

**F-minor — potential integer overflow in `symbol_cost.c` (medium on 32-bit INT builds).**
`symbol_cost.c:164,166,178`: inner sub-expressions `2 * rdofsum`, `2 * rdofnbr + 1`,
`2 * cdofnbr + 6 * rdofsum + 3` are evaluated in `INT` arithmetic before being cast to
`double`; for very large factorizations `6 * rdofsum` can overflow a 32-bit `SCOTCH_Num`,
producing a silently wrong operation-count (not a crash). Latent on 64-bit.

**F-minor — unchecked `atoi` for the `-r` root-process option** in the PT-Scotch CLIs
(`dgord.c:239`, `dgscat.c:153`, `dggath.c:155`) — a non-numeric/out-of-range value
silently becomes 0, selecting the wrong root process (misconfiguration, not memory-unsafe;
low). Number-of-parts *is* validated (`dgmap.c:192` `< 1` guard).

**F-minor — `gout` unchecked load returns and unbounded geometry count**
(`gout_c.c:206,216,219` — malformed geometry/map file yields garbage render rather than a
clean abort; `gout_c.c:359-362` — file-supplied `geomvertnbr` only checked `< 1` before
`memAllocGroup(geomvertnbr * sizeof(...))`, so a huge header value can wrap the size
computation on a 32-bit build → heap overflow; clean allocation failure on 64-bit).

**F8 — `test_scotch_arch.c` uses `argv[1]` without any argc check (high confidence;
test bug).** `test_scotch_arch.c:151` `if ((fileptr = fopen (argv[1], "w+")) == NULL)` —
main never validates `argc`, unlike every other test in the directory. Running the binary
with no argument passes `argv[1] == NULL` to `fopen` (undefined behavior per POSIX).
Harmless for CTest (always invoked with an argument) but breaks manual/harness reuse.

**F9 — stale edge count printed in `test_scotch_graph_coarsen.c` (high confidence;
cosmetic test bug).** Lines 343-346: after the third coarsening,
`SCOTCH_graphSize (&coargrafdat, &coarvertnbr, NULL);` is called with NULL for the edge
count, yet the next `printf` prints `coaredgenbr` — the value from the *previous* coarse
graph. The printed "vertices and edges" line for `SCOTCH_graphCoarsen` is wrong.

## Test-suite assessment

Classification of all 30 C tests in `src/check/`. "Output-validating" = the test (or its
CTest harness entry) asserts something about the *result*; "return-code-only" = it only
checks that API calls return 0/nonzero (per this repo's CLAUDE.md claim, now quantified).

| # | Test | Class | What is actually asserted |
|---|------|-------|---------------------------|
| 1 | test_common_file_compress | harness-validated | C code is a plain stream copy; CTest does compress→decompress→`compare_files` roundtrip (CMakeLists:126-129) |
| 2 | test_common_random | output-validating | replay determinism, cross-run difference (with SCOTCH_DETERMINISTIC inversion, lines 162-164), save/restore of RNG state |
| 3 | test_common_thread | output-validating | reduce and scan results compared to closed-form values (lines 146-163) |
| 4 | test_fibo | output-validating | randomized heap ops; min-key invariant checked exhaustively against the array (lines 203-209) |
| 5 | test_libesmumps | return-code-only | `esmumps()`/`esmumpsv()` return 0; output arrays (lasttab/petab/nvtab) never inspected |
| 6 | test_libmetis | return-code-only | 6 v3 + 3 v5 entry points called; parttab range, edgecut plausibility, perm/iperm inverse property — none checked |
| 7 | test_libmetis_dual | partial | `METIS_MeshToDual` compared to hardcoded golden CSR (lines 129-140) — real; `METIS_PartMeshDual` only `objval >= 0` (line 157), epart/npart unchecked |
| 8 | test_multilib | return-code-only | loads graph via 32- and 64-bit variants; **never compares `vertnbr == vertnbr_64`** (lines 114-115) — the one obvious assertion is missing |
| 9 | test_scotch_arch | return-code-only | 20 arch build/save/load calls; reloaded archs never compared to originals (no archName/re-save diff) |
| 10 | test_scotch_arch_deco | return-code-only | archBuild0/2 + sub + save/load roundtrip, no content comparison |
| 11 | test_scotch_context | smoke | threading/context API driven; only printf output, no assertions beyond return codes |
| 12 | test_scotch_dgraph_band | return-code-only | band graph built; **no `SCOTCH_dgraphCheck` on the band graph**, labels dumped to file unvalidated |
| 13 | test_scotch_dgraph_check | output-validating | that *is* the library self-check (`dgraphCheck` after load) |
| 14 | test_scotch_dgraph_coarsen | weak partial | only `coarvertlocnbr <= coarvertlocmax` (line 219); no dgraphCheck on coarse graph, multloctab never validated (contrast the sequential coarsen test) |
| 15 | test_scotch_dgraph_grow | return-code-only | grown-region part array written to file, nothing asserted (seeds may even collide, lines 174-176) |
| 16 | test_scotch_dgraph_induce | output-validating | `dgraphCheck` on induced graph (line 191) |
| 17 | test_scotch_dgraph_order | output-validating | identity permutation for empty list (lines 293-297); list-ordered-first property — but only proc 0's own local list is checked (lines 333-334), other ranks' list vertices unverified |
| 18 | test_scotch_dgraph_redist | return-code-only | **most glaring**: `dgraphCheck` on the *source* (line 147) but never on the redistributed graph; result discarded |
| 19 | test_scotch_graph_coarsen | output-validating | mate-array symmetry and multinode-array invariants (checkFineCoar/checkCoarMult); coarse graph itself never `graphCheck`'d |
| 20 | test_scotch_graph_color | output-validating | proper-coloring check over all edges (checkColor, lines 95-110) |
| 21 | test_scotch_graph_diam | return-code-only | `diamval >= 0`; no bounds vs. known graph diameters despite fixed inputs (m16x16 has known diameter) |
| 22 | test_scotch_graph_dump | harness-validated | C code only saves; CTest regenerates the graph from `gdump`-emitted C and `compare_files` against the original (CMakeLists:258-269) — genuine roundtrip |
| 23 | test_scotch_graph_induce | output-validating | `graphCheck` on both induced graphs; selection semantics (right vertices kept) not verified |
| 24 | test_scotch_graph_map | return-code-only | 2 strategies x 4 archs x 7 types incl. fixed-vertex and remap variants — **fixed vertices are never verified to remain in their prescribed parts**, parttab range never checked |
| 25 | test_scotch_graph_map_copy | return-code-only | map + remap-with-copied-partition; parttab never inspected |
| 26 | test_scotch_graph_order | output-validating | `SCOTCH_graphOrderCheck` after full and list ordering (lines 142, 163); Save* return codes ignored |
| 27 | test_scotch_graph_part_ovl | prints-only | computes per-part loads and prints them (lines 185-204); asserts nothing (no balance bound, no partval < partnbr check — an out-of-range partval would index loadtab OOB in the *test*) |
| 28 | test_scotch_mesh_graph | return-code-only | `SCOTCH_meshGraph` returns 0; resulting graph not even `graphCheck`'d |
| 29 | test_strat_par | no assertions | `stratDgraphMapBuild/OrderBuild` return values ignored entirely |
| 30 | test_strat_seq | no assertions | same pattern, sequential |

(The Fortran `test_libmetis_dual_f.f90.in` mirrors #7: golden-array check for MeshToDual.)

**Tally:** 10/30 output-validating (4 of them only via the library's own `*Check`
routine), 2/30 validated by the CTest harness via golden files, 2/30 partial/weak,
**16/30 return-code-only or assertion-free (53%)** — CLAUDE.md's claim is confirmed and
now itemized. Note the inverse correlation: the internal-API tests (fibo, common_thread,
common_random) are the *strongest*, while the public-API compat layers (libmetis,
libesmumps) and the mapping/partitioning tests — Scotch's core deliverable — are the
weakest.

**libscotch subsystems with zero direct `src/check` coverage** (CLI-only or nothing):

- `SCOTCH_graphPart`/`graphMapView` k-way with real target files (gpart/gmap/gmtst only);
  `SCOTCH_dgraphPart`/`dgraphMap` (dgpart CLI only).
- All geometry APIs (`SCOTCH_geom*`, `graphGeomLoad/Save`) — gout/gcv only, and gcv is
  fully untested.
- `SCOTCH_meshOrder`, mesh save/check APIs (mord/mtst only); `SCOTCH_meshLoad` appears
  only as setup in test_scotch_mesh_graph.
- `SCOTCH_graphStat`, `SCOTCH_dgraphStat`, `SCOTCH_archName/archSize` introspection.
- Strategy *parsing* error paths (`SCOTCH_stratGraphMap` with invalid strings).
- Fortran API (only the METIS-dual Fortran test exists; no Fortran test of libscotch
  proper in `src/check` — the `*_f` interface files in libscotch are untested here).

**Minimal high-value test additions for upstream** (ordered by value/effort):

1. `test_multilib`: add `if (vertnbr != (SCOTCH_Num) vertnbr_64) exit(FAILURE)` — one line,
   makes the test non-vacuous.
2. `test_scotch_dgraph_redist`: `SCOTCH_dgraphCheck (&dstgrafdat)` + compare global
   vertex/edge counts before/after — turns the weakest dgraph test into a real one.
3. `test_scotch_graph_map`: after each compute, assert `0 <= parttab[v] < archsiz`
   (non-variable archs) and that fixed vertices kept their prescribed part — this is the
   only test of `graphMapFixedCompute`/`graphRemapFixedCompute` and currently cannot
   detect a fixed-vertex regression.
4. `test_scotch_mesh_graph`: `SCOTCH_graphCheck` on the result + golden vertex/edge counts
   for ship001.msh.
5. `test_libmetis`: check parttab range, that `edgecut` equals an independently recomputed
   cut, and that `perm`/`iperm` are mutually inverse (would immediately document the
   swapped-convention behavior, and would have caught F1 if a NULL-ubvec case were added).
6. `test_scotch_graph_part_ovl`: assert `-1 <= partval < partnbr` and a load-balance bound
   derived from the strategy's bal parameter.
7. Coarse-graph `SCOTCH_graphCheck`/`dgraphCheck` in both coarsen tests.
8. A `gcv` CTest entry (roundtrip a graph through a foreign format with `compare_files`).

## PyScotch relevance

Porting status per `tests/scotch_ports/PORTING_STATUS.md` (repo root):

- **Bookkeeping gap:** PORTING_STATUS.md says "All 29 Scotch C tests" but `src/check/`
  has **30** C tests. `test_scotch_graph_map.c` and `test_scotch_graph_order.c` appear in
  no table and have no `tests/scotch_ports/test_*.py` counterpart (verified by directory
  listing and grep: no port exercises `graphMapFixedCompute`, `graphRemapCompute`, or
  `graphOrderComputeList`; only `map_copy` covers `graphMapCompute`, and `OrderCheck`
  appears only in `pyscotch_base/test_graph_advanced.py` / `test_interop.py`). These two
  are precisely the C tests covering remapping, fixed vertices, and list-based ordering —
  the least-validated core paths. They should be ported (and strengthened per items 3
  above) or explicitly listed as covered-elsewhere with evidence.
- **Ports whose C original is vacuous — strengthen, don't mirror:** the ported
  `test_multilib.py`, `test_scotch_mesh_graph.py`, `test_scotch_graph_diam.py`,
  `test_scotch_graph_part_ovl.py` inherit C tests from the return-code-only column above.
  Worth verifying each Python port adds the missing assertion (e.g. multilib size
  comparison, mesh_graph `graphCheck`, part_ovl part-range/balance) rather than
  reproducing the vacuous pass. The CLAUDE.md rule "keep the exact same assertions" sets
  a *floor*, not a ceiling — these are the files where the ceiling matters.
- **dgraph_coarsen guidance conflict:** the C test exits the coarse dgraph even on
  return 1 (`test_scotch_dgraph_coarsen.c:236`), while this repo's CLAUDE.md forbids it.
  Good candidate for `QUESTIONS_FOR_SCOTCH_TEAM.md` — upstream's own test either
  contradicts the real contract or proves `dgraphExit` is safe there.
- **METIS bindings (currently blocked on "missing libscotchmetis bindings"):** when they
  land, F1-F4 above are directly relevant: bind the v5 API with `ubvec=None` support only
  after F1 is fixed or guarded in the wrapper; do not expose `ncon > 1` (silently wrong);
  document the perm/iperm swap; treat `ParMETIS_V3_NodeND` error returns on non-power-of-2
  comm sizes as "ordering still valid".
- Harness-validated C tests (`graph_dump`, `file_compress`, gbase/gtst/dgscat-dggath) get
  their real assertions from CTest `compare_files`, not the C code — Python ports based
  only on the `.c` source will miss the golden-file comparison that is the actual test.
- The two esmumps in-tree tests (`esmumps/test_esmumps.c`, `esmumps/test_fax.c`) are
  smoke tests: `test_esmumps` asserts only `ncmpa >= 0`; `test_fax` asserts
  `symbolFaxGraph`/`symbolCost` return 0 and prints NNZ/OPC without checking values. A
  PyScotch esmumps binding should assert the produced permutation is a valid permutation
  and that NNZ/OPC match golden values for a fixed input — neither C test does.
- F5 (HAMD strategy) is a concrete upstream bug for `QUESTIONS_FOR_SCOTCH_TEAM.md`: the
  user's direct upstream channel makes this a good one to report, since it is latent
  (only MUMPS via `esmumps_strat1` with `leorval==0` hits it) and a one-character fix
  (`'h'` → `'d'`).
