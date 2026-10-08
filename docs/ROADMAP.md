# PyScotch Roadmap

**PyScotch:** 7.0.5 (2026-10-02). **Scotch pin:** 7.0.13 (7.0.16 verified
compatible on 64-bit). **Last updated:** 2026-10-08.

This file lists only what is *not* done. What is implemented is documented by
the generated API reference (`docs/site/api_data.json`, published at
https://c4ffein.github.io/pyscotch) and the version history in
[CHANGELOG.md](../CHANGELOG.md). Near-term working notes live in `tasks.md`;
upstream findings in [QUESTIONS_FOR_SCOTCH_TEAM.md](QUESTIONS_FOR_SCOTCH_TEAM.md).

## Blocked on upstream

- **Bare-letter strategy semantics.** PyScotch rejects hollow strings at
  construction and passes everything else verbatim. Whether upstream makes
  bare letters build real defaults decides which tests get deleted and
  whether the constructor check loosens. Details in `tasks.md`.
- **Strategy parser, phase 2.** The recursive-descent spike
  (`experiments/parser-rd`) matches bison byte-for-byte on valid input.
  Remaining: structured error transport, the two accept/reject trap fixes
  (empty scalar values, nested syntax-error crash), the dgraph grammars, and
  how to propose it upstream. All gated on a conversation with the Scotch team.
- **Open upstream findings.** Every entry in QUESTIONS_FOR_SCOTCH_TEAM.md is
  still open as of the 7.0.16 audit: parser SIGSEGV on nested syntax errors,
  empty-scalar corruption, `graphStat` edlosum arcs-vs-edges, `orderCheck`
  ignoring permtab, `contextOptionSetNum` switching on the value, the
  undocumented public functions, the `contextAlloc` rename-table gap, the
  missing NEEDED entries, and two dorderPerm follow-ups.
- **Static-analysis reports.** Twelve subsystem reports in
  `docs/scotch-analysis/` were never triaged into the questions file nor
  reproduced against a built library.

## Binding gaps

Functions declared in the Scotch headers with no binding in `libscotch.py`:

- **PT-Scotch:** the `dgraphHalo` family (`Halo`, `HaloAsync`, `HaloWait`,
  `HaloReqAlloc`, `HaloReqSizeof`), `dgraphMapStat`, `dgraphOrderSaveBlock`,
  `dgraphSize`, `contextBindDgraph`, and the whole `dmesh*` family.
- **Sequential:** `graphRemapView` / `graphRemapViewRaw`, `meshOrderList` /
  `meshOrderComputeList`, `meshGeomLoadHabo` / `meshGeomLoadScot` /
  `meshGeomSaveScot`, `meshBuildElem`, `archCmpltws`, the `archDom*` routines,
  `contextOptionParse`, `contextThreadImport1` / `Import2` / `Spawn`, and
  `stratFree` (its intended semantics are an open upstream question).
- **Typed strategy builder** covers sequential mapping and ordering only.
  Mesh and dgraph grammar families, and importing a `stratSave` dump back
  into builder objects, are open.
- **Mesh** has ten methods and seven tests. `Mesh.partition()` in particular
  is barely exercised.

## Testing

- Scotch 7.0.16 was only verified on 64-bit. 32-bit and the differential
  reference tools were not run against it.
- No stress tests, memory-leak tests, or error-recovery tests.
- No CI builds the parallel conda recipe or its openmpi / mpich variants. The
  package-verify job is sequential-only; the only proof is a local run from
  July 2026.
- `benchmarks/` has two scripts and no recorded results.

## Packaging and release

- **conda-forge:** recipe exists under `packaging/conda/`, nothing published.
  The install page still says "coming soon".
- **Scotch bump 7.0.13 to 7.0.16:** compatibility verified, bump not done. It
  touches the version catalog in `scotch_build.py`, the submodule, the
  scotch-build and pypi-verify CI matrices, `make docs-api`, and the golden
  files. Note the default mapping strategy changed upstream in 7.0.16, so
  partition results can differ.
- **Wheels** are Linux only (x86_64, aarch64). No macOS, no Windows.
- **README** still opens with the "vibe-engineering experiment, you probably
  shouldn't use this" warning. Removing it is the stated goal before
  approaching upstream about adoption.
- **Untracked work** not yet committed or referenced anywhere: `demo/`,
  `experiments/`, `docs/scotch-analysis/`, `tasks.md`.

## Documentation and project

- No Jupyter tutorials.
- No page on performance characteristics or wrapper overhead.
- No co-maintainers. [CONTRIBUTING.md](../CONTRIBUTING.md) does not point here.

---

**Maintainer:** @c4ffein (with AI pair-programming assistance from Claude)
