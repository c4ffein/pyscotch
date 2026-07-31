# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
