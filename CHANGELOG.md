# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
