# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- **Default variant is now 64-bit sequential** (`PYSCOTCH_INT_SIZE=64`, `PYSCOTCH_PARALLEL=0`; was 32/0 in code, documented as 64/1). 64-bit indices are safe at any graph size, and a sequential default is required for the binary wheels, which do not ship PT-Scotch. Conda's 32-bit Scotch users must set `PYSCOTCH_INT_SIZE=32` (the load-time width check says so explicitly).

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
