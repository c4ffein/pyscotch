# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **`Dgraph.build` handed Scotch pointers into freed memory.** `SCOTCH_dgraphBuild`
  does not copy its input arrays (it stores the pointers for the life of the
  graph), and the copies PyScotch made to convert their dtype were dropped when
  `build()` returned. Any input needing a conversion (a Python list, or int32
  arrays on a 64-bit build) left the distributed graph reading garbage once the
  heap was reused; `check()` flipped to false and every later operation ran on
  corrupt data. The Dgraph now keeps a reference to every array it handed to
  Scotch, like the sequential `Graph.build` always did. `grow`, `band`,
  `redist` and `induce_part` now also accept arrays of any integer width
  (converted for the duration of the call); `grow`'s in-place output array
  `partgsttab` (and `build`'s `edgegsttab`) must already have the Scotch dtype
  and is refused with a `TypeError` otherwise, since a converted copy would
  silently swallow the results. Pinned by
  `tests/scotch_ports_mpi/mpi_scripts/dgraph_array_lifetime.py`.
- **`Dgraph.grow` / `Dgraph.band` overflowed short seed arrays.** At the C
  level `SCOTCH_dgraphGrow` and `SCOTCH_dgraphBand` re-use the seed (frontier)
  array as their breadth-first queue, so it must hold `vertlocnbr` entries and
  its contents are clobbered (PT-Scotch manual; `dgraph_band_grow.c`). The
  wrappers passed the caller's array straight through without saying so; a
  seed array shorter than that corrupted the heap (found as a
  layout-dependent crash in `MPI_Finalize`). Both now copy the seeds into a
  private, correctly sized work array, so any array of at least
  `seedlocnbr` / `fronlocnbr` entries is safe and the caller's array is left
  untouched.
- `tests/pyscotch_base/test_context.py::test_bind_graph` now closes its
  Context. Binding a graph starts Scotch's thread pool, which pins the calling
  thread to one core and only unpins it in `SCOTCH_contextExit`; the leaked
  Context left the whole pytest process, and every `mpirun` it spawned
  afterwards, confined to a single CPU.
- **`Graph.from_edges(edge_weights=...)` could never be used**: it passed one
  weight per input edge where Scotch needs one load per arc, so the length
  check always raised. Each weight is now applied to both arcs of its edge.
  `vertex_weights` accepts numpy arrays (the old truthiness test raised on
  them). Self-loops and duplicate edges (in either direction) are now rejected
  with a `ValueError` instead of silently building a graph whose own
  `check()` fails, matching `from_scipy_sparse` / `from_networkx`; negative
  vertex indices are rejected too, and any iterable of pairs (a set, a
  generator) is accepted.
- `libscotch.to_scotch_array` now also guarantees C-contiguity: a strided view
  used to hand Scotch a pointer into interleaved memory.
- The MPI test orchestrator (`tests/scotch_ports_mpi/test_dgraph.py`)
  hard-coded `PYSCOTCH_INT_SIZE=64` for its child processes, so the "32-bit
  parallel" quadrant of `make test-quadrant` ran every MPI script against the
  64-bit library. Children now follow the quadrant under test.

## [7.0.4] - 2026-08-11

Small additive release: a public sequential mapping entry point, and the
byte-identity differential tier broadened to ordering, mapping, and the
distributed tools. No library-code or Scotch-version changes.

### Added
- **`Graph.map(arch, strategy=None)`**: public sequential mapping onto an
  arbitrary target architecture (hypercube, mesh, real machine topology, …).
  Partitioning is the special case of mapping onto a complete graph; this
  generalizes it, mirroring Scotch's `gmap`. Previously only `partition()` and
  the distributed `Dgraph.map()` were public — the sequential mapping plumbing
  existed but had no entry point.
- Differential test tier extended to prove **byte-identity with Scotch's own
  CLI tools** under deterministic settings: `gord` (ordering) and `gmap`
  (mapping) sequentially, and — under `mpirun` — `dgpart`/`dgord` (distributed
  partition and ordering). Built and run via `make build-reference-tools` +
  `make test-differential`; CI fails loudly if any reference tool is missing.

### Notes
- Reproducing `dgpart`/`dgord` byte-for-byte from the distributed API requires
  seeding the PRNG **per process** — `random_proc(rank)`, the CLI tools' first
  PRNG action — not just `random_reset()`. Without it, weighted or large graphs
  compute a different (still valid) distributed result. See the fold-dup note in
  `QUESTIONS_FOR_SCOTCH_TEAM.md`.

## [7.0.3] - 2026-08-09

Scotch 7.0.13 release: catalog, submodule and bundled wheel libraries all move
to the new upstream version — the first release where the newest Scotch builds
pristine, with no PyScotch quickfix.

### Added - Scotch 7.0.13
- `pyscotch scotch build` knows 7.0.13 (sha256-pinned GitLab tarball);
  `latest_version()` — and therefore the no-argument `build` default — now
  resolves to 7.0.13. **No quickfix patch is needed**: upstream merged exactly
  the fix our bundled 7.0.12 patch carried (`SCOTCH_memFree` and
  `SCOTCH_meshBuildElem` registered in the rename table, `module.h`), so
  7.0.13 is also the new `latest_pristine_version()`. The 7.0.12 catalog
  entry and its quickfix are kept for reproducible older builds.
- `external/scotch` submodule bumped to v7.0.13; wheels bundle 7.0.13
  sequential libraries. Full suite green against 7.0.13 in all four
  int-size/variant quadrants (64/32-bit x sequential/parallel).

### Changed
- `Verify published PyPI release` workflow now builds a **matrix of
  catalogued Scotch versions** in parallel jobs, each with its quickfix
  expectation pinned: 7.0.12 must be auto-patched, 7.0.13 must build
  pristine. Adding a future release (7.0.14, ...) to the certification is a
  one-line matrix entry. The bundled-wheel API/CLI smoke moved to its own
  lighter job (no MPI toolchain needed there).
- Its repo-side twin `Build Scotch from CLI (end-to-end)` is matrixed the
  same way (7.0.11, 7.0.12, 7.0.13 in parallel jobs — the weekly tarball
  drift watchdog now covers every catalogued version at once, where it
  previously never exercised the newest release). Version-specific checks
  ride on matrix fields: the exported-symbol check (`symbol`) and the
  `--pristine`-must-fail-with-this-diagnosis negative test (`pristine_grep`)
  run only where they apply.

### Notes
- Analysis of a PT-Scotch `dorderPerm` debug-build bug reported via PETSc
  (untyped `DORDERCBLKNONE` leaf placeholders + a non-collective debug check;
  latent for years, surfaced by 7.0.13's CMake `SCOTCH_DEBUG_ALL` propagation
  fix) is documented in `QUESTIONS_FOR_SCOTCH_TEAM.md`. PyScotch is not
  affected: `order_compute()` raises on failure, so `order_perm()` never runs
  on a failed ordering — and wheels ship the sequential library only.

## [7.0.2] - 2026-07-31

Verification-hardening release: no library code changes, but the release
pipeline now proves much more before and after publishing.

### Added - CI verification coverage
- New `Verify published PyPI release` workflow (manual dispatch): the literal
  end-user journey with **no repo checkout** — `pip install pyscotch` from the
  real index, partition/order through the bundled wheel libraries, CLI smoke,
  then `pyscotch scotch build 7.0.12 --parallel` from the upstream tarball and
  a PT-Scotch `Dgraph` run under `mpirun`.
- `Build Scotch from CLI (end-to-end)` now runs weekly (upstream-tarball
  drift watchdog: catches a regenerated/moved GitLab archive even when no
  PyScotch file changed), actually *partitions* through the quickfixed 7.0.12
  build instead of only loading it, and additionally builds 7.0.12
  `--parallel` and drives `Dgraph` under `mpirun` through it.
- Install/wheel smoke tests now also exercise the `pyscotch` console script
  (`doctor` + `partition` on a saved graph): broken entry-point wiring in a
  wheel previously passed every import-based check.

### Fixed
- The golden-master walkthrough normalizes PyScotch's own version to
  `<VERSION>`, so the goldens validate both the dev tree (unstamped) and a
  tag-stamped published sdist; previously a published sdist failed the byte
  comparison on version lines alone.

## [7.0.1] - 2026-07-30

### Added - Fail-fast strategy-string checking
- `Strategy(string)` now probes the string under all three sequential-graph
  grammars (mapping, ordering, overlap) at construction: strings that parse
  under none raise `ValueError` immediately, and so do *hollow* strings —
  ones that parse but leave strategy-valued slots as do-nothing dummies (bare
  `"m"`, or `"r{job=t,map=t,poli=S,bal=0.05}"` which omits `sep=`). Hollow
  slots are detected by round-tripping through `SCOTCH_stratSave`, which
  serializes them as empty parameters — the library itself is the detector.
  `""` keeps its documented verbatim pass-through. Wrong-grammar use errors
  now name the grammars that DO accept the string ("valid under the ORDERING
  grammar only").

### Added - Typed strategy-grammar builder (`pyscotch.strategy_grammar`)
- Compose strategy strings as typed trees — `Mapping.Multilevel(low=
  Mapping.Recursive(sep=Seq(Bipart.Gg(), Bipart.Fm())), asc=Mapping.Fm())` —
  rendering to plain Scotch grammar strings (`str(tree)`). Strategy-valued
  parameters are *required* arguments, so stratdummy slots are
  unrepresentable; numeric/case parameters render only when set, so Scotch's
  own defaults always apply. Four namespaces mirror the `*_st.c` method
  tables (`Mapping`, `Bipart`, `Ordering`, `Separation`, 29 methods, named
  after upstream's routine suffixes), plus `Seq`/`Select` combinators and the
  `Raw` escape hatch. `tree.validate()` parses with the live library and
  returns the canonical form; a drift-guard test renders every method against
  the live parser so upstream grammar changes turn the suite red.

### Added - Differential testing against Scotch's own tools
- `tests/pyscotch_base/test_differential_gpart.py`: under deterministic
  settings, PyScotch's partition of a graph is **byte-identical to `gpart`'s
  mapping file** (opt-in via `PYSCOTCH_GPART`). First run caught a real bug —
  see Fixed below.
- `Graph.load(filename, baseval=0)` gained the `baseval` parameter with
  `SCOTCH_graphLoad`'s exact semantics: `-1` preserves the file's own vertex
  numbering base like the C tools do (default `0` still rebases).

### Fixed
- **Wheel builds of Scotch 7.0.12 failed** (the submodule's rename-table bug,
  hard error on modern GCC — and a silently missing public symbol on older
  GCC). Builds now compile Scotch in a disposable, quickfix-patched copy
  (`build/scotch-src`) prepared by `pyscotch scotch prepare`; the git
  submodule is never modified. New CLI: `pyscotch scotch patch <srcdir>`
  (apply the bundled quickfixes to any Scotch tree, version auto-detected,
  idempotent) and `pyscotch scotch prepare --dest DIR`. One patch catalog,
  one applier, shared by tarball builds, dev builds and wheels. A new
  equivalence-guard test fails if the submodule is ever bumped past the
  catalog again.
- `Graph.save_mapping` now labels vertices with the graph's base value, as
  `gpart`/`gmap` do; a mapping saved for a based graph previously used
  0-based labels and could not be paired with its graph by Scotch tools.

### Changed - Strategy semantics: None is the default, strings are verbatim
- **The default strategy is spelled `None` (or a fresh `Strategy()`, or
  `reset()`); every string — `""` included — is passed to Scotch verbatim.**
  All five string setters (`set_mapping`, `set_ordering`,
  `set_overlap_partitioning`, `set_dgraph_mapping`, `set_dgraph_ordering`)
  and the `Strategy(strategy_string)` constructor now accept `None` as
  "Scotch's default". `""` is no longer intercepted: at the C level it parses
  into a do-nothing strategy (mapping leaves every vertex unassigned at -1,
  ordering returns the identity permutation), and PyScotch now reproduces
  that behaviour exactly — same string, same meaning as C Scotch.
- `Strategies.DEFAULT_PARTITION` / `Strategies.DEFAULT_ORDER` are now `None`
  (previously `""`).
- `Graph.partition_overlap` pre-fills its output with -1: a do-nothing
  overlap strategy (e.g. `""`) at the C level returns without writing the
  output array at all, which would otherwise surface uninitialized memory
  that can look like a valid partition.
- Fixed: released 7.0.0 routed its *default* strategy paths through
  `SCOTCH_stratGraphMap("")`, shipping a partitioner that returned all -1;
  defaults now go through untouched strategies, which Scotch fills with its
  real adaptive default.
- Removed stale `SCOTCH_randomReset` from the advertised C functions of
  `Graph.partition` / `Graph.color` (neither touches the PRNG; the policy is
  no implicit resets anywhere — call `pyscotch.random_reset()` yourself).

### Removed - `Strategy.set_multilevel()` / `set_nested_dissection()`
- **`Strategy.set_multilevel()` and `Strategy.set_nested_dissection()` are
  gone.** Scotch's default strategy *is* multilevel (and its default ordering
  *is* nested-dissection based); the `SCOTCH_strat*Build` API has no flag to
  select either explicitly, so the only honest implementation was an alias of
  the default build — a method that implies a selection mechanism upstream
  does not have. In released 7.0.0 they were worse than useless: they passed
  the bare `"m"` / `"n"` strategy strings, whose implicit sub-strategies are
  do-nothing dummies (every vertex in one part / identity permutation), so no
  working usage exists to stay compatible with. Migration: use a plain
  `Strategy()` — that IS multilevel / nested dissection — or
  `request_mapping(...)` / `request_ordering(...)` with `StrategyFlags` to
  tune it. `set_recursive_bisection()` stays: `SCOTCH_STRATRECURSIVE` is a
  genuine upstream selector.
- The CLI keeps `-s multilevel` (partition) and `-s nested` (order) as
  documented **synonyms of `default`**: at the command line the word names
  the algorithm you get — and you really do get a multilevel partition /
  nested-dissection ordering — rather than a distinct selection mechanism.

## [7.0.0] - 2026-07-13

### Changed - Versioning scheme
- Versions now mirror the supported Scotch series: `X.Y` = Scotch major.minor
  (7.0.x), the patch digit is PyScotch's own release counter. Hence the jump
  from 0.2.0 to 7.0.0.

### Added - Interop
- `Graph.from_scipy_sparse()` / `Graph.to_scipy_sparse()` — exact CSR round-trips, strict symmetry/self-loop/weight validation
- `Graph.from_networkx()` / `Graph.to_networkx()` — arbitrary node labels via `(graph, nodes)` mapping
- `interop` optional dependency extra (`pip install "pyscotch[interop]"`)

### Added - Packaging & Distribution
- Binary wheel pipeline: `.github/workflows/wheels.yml` (cibuildwheel, manylinux_2_28, x86_64 + aarch64), `scripts/build_wheel_libs.sh`, `MANIFEST.in`; wheels bundle sequential Scotch (32- and 64-bit) and are tagged `py3-none-<platform>`
- System-Scotch support: automatic fallback to distro/conda `libscotch` (dlopen by soname), `PYSCOTCH_SYSTEM=1` to force it, `PYSCOTCH_LIB_DIR` explicit override
- Unsuffixed-symbol support with integer-width verification via `SCOTCH_numSizeof()` — unblocks conda-forge (`packaging/conda/meta.yaml` recipe skeleton)
- `c_fopen` falls back to the platform libc when no compat shim is present (system-Scotch mode)

### Added - Verification & Testing
- `tests/pyscotch_base/test_binding_signatures.py` — every ctypes binding diff-checked against the parsed Scotch headers (existence, arg counts, arg types, return types)
- 26 behavioral tests upgrading coverage: save/load roundtrips parsed back, hand-checked `graphStat`/mesh duals, context determinism, all 10 architecture topologies, `dgraphCoarsenVertLocMax` under mpirun
- 42 interop tests (round-trips, validation errors, karate-club end-to-end partition)

### Added - Documentation
- Auto-generated API reference (`docs/site/gen_api.py`) from the `@scotch_binding` decorator registries, with coverage stats
- SVG diagrams replacing ASCII art (triangle graph, multilevel V-cycle, architecture layers); flat single-surface site theme; GitHub Primer syntax highlighting
- `docs/FINDINGS.md` — index of all internal and upstream findings

### Changed
- **Default variant is now 64-bit sequential** (`PYSCOTCH_INT_SIZE=64`, `PYSCOTCH_PARALLEL=0`; was 32/0 in code, documented as 64/1). 64-bit indices are safe at any graph size, and a sequential default is required for the binary wheels, which do not ship PT-Scotch. conda-forge's `scotch` is 64-bit, so it matches the new default; a mismatched-width system Scotch gets a load-time error naming the correct `PYSCOTCH_INT_SIZE`.

### Fixed - Binding signatures (found by the new signature verifier)
- `SCOTCH_meshBuild` (missing parameter), `SCOTCH_meshData` (3 missing parameters), `SCOTCH_dgraphData` (misaligned 16/17 layout)
- `SCOTCH_version` now uses `int*` per the header (was `SCOTCH_Num*`)
- `SCOTCH_memCur`/`SCOTCH_memMax` return `SCOTCH_Idx` (was wrong-width `c_long` on 32-bit)
- `Dgraph.data()` MPI communicator buffer widened to `c_void_p` — was a 4-byte buffer receiving an 8-byte OpenMPI handle (memory corruption)
- `SCOTCH_memFree` resolved despite upstream exporting it unsuffixed

### Upstream (reported in docs/QUESTIONS_FOR_SCOTCH_TEAM_2.md)
- Scotch 7.0.12 does not build with `SCOTCH_RENAME_ALL` (`SCOTCH_meshBuildElem` missing from module.h) — verified fix in `patches/scotch-7.0.12-rename-all-fix.patch`; full suite passes on patched 7.0.12
- `SCOTCH_memFree` missing from the module.h rename table (7.0.11 and 7.0.12)
- `SCOTCH_contextOptionSetNum` switches on the option value instead of the option index

## [0.2.0] - 2025-11-18

### Added - Distributed Graph Operations (Phase 1 Complete! 🎉)
- **NEW:** `Dgraph.ghst()` - Compute ghost edge array for distributed graphs
- **NEW:** `Dgraph.grow()` - Grow subgraphs from seed vertices (adaptive mesh refinement)
- **NEW:** `Dgraph.band()` - Extract band graph from frontier (sparse matrix reordering)
- **NEW:** `Dgraph.redist()` - Redistribute graph across processes (dynamic load balancing)
- **NEW:** `Dgraph.induce_part()` - Extract induced subgraph from partition (hierarchical partitioning)
- **100% Scotch Coverage:** All 6 Scotch distributed graph operations now implemented!

### Added - Testing & Validation
- Integration test: Sequential partitioning workflow (end-to-end)
- Integration test: Distributed coarsening workflow (MPI)
- Integration test: Mesh partitioning workflow
- 4 new MPI test ports matching Scotch C tests exactly:
  - `dgraph_grow.py` - Region growing test
  - `dgraph_band.py` - Band graph extraction test
  - `dgraph_redist.py` - Graph redistribution test
  - `dgraph_induce_part.py` - Induced subgraph test
- Total test count: 192 passing tests (was 188)

### Added - Examples & Documentation
- `examples/distributed_coarsening.py` - MPI coarsening example
- `examples/mesh_partitioning.py` - Mesh partitioning example
- `examples/README.md` - Comprehensive examples documentation
- `benchmarks/benchmark_sequential_partitioning.py` - Performance benchmarking
- `benchmarks/benchmark_distributed_operations.py` - MPI benchmarking
- `benchmarks/README.md` - Benchmark documentation
- Updated `ROADMAP.md` - Phase 1 complete, now 80% overall completion
- Updated `MPI_TEST_COVERAGE.md` - 100% coverage achieved

### Added - Build & Development
- `make test` now runs `pytest -vvvv` for detailed test output
- Makefile improvements for better developer experience

### Changed
- Project completion: 65% → 80% (Phase 1 complete)
- MPI test coverage: 33% → 100% (6/6 operations)
- Documentation updated to reflect new capabilities

### Performance
- All distributed operations tested and validated
- Benchmarks available for performance comparison
- Ready for production distributed graph processing

## [0.1.0] - 2024-XX-XX

### Added
- Initial release
- Graph partitioning support
- Mesh partitioning support
- Sparse matrix ordering support
- Command-line interface
- Python API with type hints
- PT-Scotch library integration
- Makefile-based build system

[Unreleased]: https://github.com/c4ffein/pyscotch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/c4ffein/pyscotch/releases/tag/v0.1.0
