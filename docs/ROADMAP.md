# PyScotch Roadmap

**Version:** 0.1.0 (Alpha) → 0.2.0 (Target)
**Last Updated:** 2025-11-18

This document provides an honest assessment of what's implemented, what's in progress, and what's planned for PyScotch.

🎉 **Phase 1 Complete!** All Scotch distributed graph operations are now implemented and tested!

---

## ✅ Fully Implemented & Tested

### Core Infrastructure
- ✅ **Multi-variant architecture** - Load 4 Scotch variants simultaneously (32/64-bit × sequential/parallel)
- ✅ **FILE* compatibility layer** - `libpyscotch_compat.so` for cross-platform FILE* handling
- ✅ **RAII resource management** - Automatic cleanup with context managers
- ✅ **Type hints** - Full typing support for better IDE experience

### Sequential Graph Operations (Graph class)
- ✅ `Graph.load()` - Load from Scotch .grf format
- ✅ `Graph.save()` - Save to Scotch .grf format
- ✅ `Graph.build()` - Build from arrays
- ✅ `Graph.from_edges()` - Create from edge list
- ✅ `Graph.check()` - Validate graph structure
- ✅ `Graph.size()` - Get vertex/edge counts
- ✅ `Graph.partition()` - Graph partitioning
- ✅ `Graph.order()` - Graph ordering for sparse matrices
- ✅ `Graph.save_mapping()` - Save partition to file

### Distributed Graph Operations (Dgraph class)
- ✅ `Dgraph.__init__()` - Initialize distributed graph
- ✅ `Dgraph.load()` - Load distributed graph
- ✅ `Dgraph.build()` - Build from distributed arrays
- ✅ `Dgraph.check()` - Validate distributed graph (tested with MPI)
- ✅ `Dgraph.data()` - Get graph data with selective field retrieval ⭐
- ✅ `Dgraph.coarsen()` - Graph coarsening (all 3 modes: plain, fold, folddup) ⭐
- ✅ `Dgraph.coarsen_vert_loc_max()` - Get multinode array size
- ✅ `Dgraph.ghst()` - Compute ghost edge array ⭐ NEW!
- ✅ `Dgraph.grow()` - Grow subgraphs from seeds ⭐ NEW!
- ✅ `Dgraph.band()` - Extract band graph ⭐ NEW!
- ✅ `Dgraph.redist()` - Redistribute graph across processes ⭐ NEW!
- ✅ `Dgraph.induce_part()` - Extract induced subgraph ⭐ NEW!

### Supporting Classes
- ✅ **Strategy** - Partitioning/ordering strategies
  - `Strategy.set_mapping_default()`
  - `Strategy.set_ordering_default()`
  - `Strategy.set_recursive_bisection()`
  - `Strategy.set_multilevel()`
  - `Strategy.set_nested_dissection()`
- ✅ **Strategies** - Pre-defined strategy factories
  - `Strategies.partition_quality()`
  - `Strategies.partition_fast()`
  - `Strategies.order_quality()`
  - `Strategies.order_fast()`
- ✅ **Architecture** - Target architectures
  - `Architecture.complete()` - Complete graph
  - `Architecture.complete_graph()` - Static method
- ✅ **Mapping** - Partition assignments
  - Save/load, analyze balance, access partitions
- ✅ **Ordering** - Vertex orderings
  - Apply/inverse, save/load
- ✅ **Mesh** - Basic mesh operations
  - `Mesh.load()`, `Mesh.save()`
  - `Mesh.check()`, `Mesh.to_graph()`
  - `Mesh.partition()` ⚠️ (minimal testing)

### Testing
- ✅ **177 unit tests** for sequential operations
- ✅ **11 MPI tests** for distributed operations ⭐ NEW!
  - `test_dgraph_init` - Initialization
  - `test_dgraph_build` - Building graphs
  - `test_dgraph_check` - Validation (2 tests)
  - `test_dgraph_coarsen` - Coarsening (3 tests)
  - `test_dgraph_grow` - Region growing ⭐ NEW!
  - `test_dgraph_band` - Band graph extraction ⭐ NEW!
  - `test_dgraph_redist` - Graph redistribution ⭐ NEW!
  - `test_dgraph_induce_part` - Induced subgraph ⭐ NEW!
- ✅ **Compatibility tests** - Verify library builds (4 tests)

**Total: 192 passing tests** ✨

---

## 🚧 Partially Implemented

### Mesh Operations
- ✅ Basic load/save/partition
- ❌ Advanced mesh operations
- ❌ Limited test coverage

---

## ❌ Not Implemented (High Priority)

### Missing Testing
- ❌ **Integration tests** - No end-to-end workflow tests
- ❌ **Performance benchmarks** - No performance validation
- ❌ **Stress tests** - No large-scale testing

### Missing Infrastructure
- ❌ **Command-Line Interface** - Documented but not implemented
- ❌ **Examples directory** - Referenced but missing
- ❌ **Documentation examples** - Need real working examples

---

## 🐛 Known Issues

### FILE* Limitations
Despite `libpyscotch_compat.so`, **9 tests still blocked** by FILE* issues:
- Complex FILE* operations (dump, mapping save/load to FILE*)
- Need investigation to determine workarounds

### Documentation Issues
- ✅ **FIXED**: API.md now warns CLI is not implemented
- ⚠️ **REMAINING**: Need examples/ directory with working code
- ⚠️ **REMAINING**: Some documented workflows need validation

---

## 📋 Implementation Plan

### Phase 1: Complete Core Distributed Operations ✅ COMPLETE!
**Goal:** Achieve feature parity for documented distributed operations

- [x] Implement `Dgraph.band()` with test ✅
- [x] Implement `Dgraph.grow()` with test ✅
- [x] Implement `Dgraph.induce_part()` with test ✅
- [x] Implement `Dgraph.redist()` with test ✅
- [x] Implement `Dgraph.ghst()` (prerequisite for grow) ✅

**Impact:** 100% of Scotch distributed graph operations now implemented! 🎉

### Phase 2: Integration Testing (Priority 2)
**Goal:** Validate real-world workflows

- [ ] Integration test: Sequential partitioning workflow
  - Load graph → partition → save mapping → validate
- [ ] Integration test: Distributed coarsening workflow
  - Load distributed graph → coarsen → validate → compare with Scotch
- [ ] Integration test: Mesh partitioning workflow
  - Load mesh → partition → convert to graph → validate

### Phase 3: Performance Validation (Priority 3)
**Goal:** Ensure performance is acceptable

- [ ] Benchmark: Sequential partitioning vs native Scotch
- [ ] Benchmark: Distributed operations vs native PT-Scotch
- [ ] Benchmark: Memory overhead of Python wrapper
- [ ] Document performance characteristics

### Phase 4: User Experience (Priority 4)
**Goal:** Make library easy to use

- [ ] Create `examples/` directory
  - `simple_partition.py`
  - `distributed_coarsening.py`
  - `mesh_partitioning.py`
  - `graph_ordering.py`
- [ ] Implement CLI (optional, documented in API.md)
- [ ] Add Jupyter notebook tutorials

### Phase 5: Production Hardening (Priority 5)
**Goal:** Make production-ready

- [ ] Investigate and resolve 9 FILE* blocked tests
- [ ] Add stress tests (large graphs, many processes)
- [ ] Add error recovery testing
- [ ] Memory leak testing
- [ ] Consider co-maintainers

---

## 🎯 Version Targets

### v0.2.0 (Target: Q1 2025)
- ✅ All 4 remaining Dgraph operations implemented **COMPLETE!** 🎉
- [ ] Integration tests
- [ ] Examples directory

### v0.3.0 (Target: Q2 2025)
- ✅ Performance benchmarks
- ✅ CLI implementation
- ✅ Resolve FILE* issues

### v1.0.0 (Target: Q3 2025)
- ✅ Production-ready
- ✅ Comprehensive documentation
- ✅ Co-maintainers onboarded
- ✅ Stress testing complete

---

## 📊 Current Status Summary

| Category | Implemented | Total | Percentage |
|----------|-------------|-------|------------|
| **Core Infrastructure** | 4/4 | 100% | ✅ Complete |
| **Sequential Graph Ops** | 9/9 | 100% | ✅ Complete |
| **Distributed Graph Ops** | 12/12 | 100% | ✅ Complete ⭐ NEW! |
| **MPI Tests** | 11/11 | 100% | ✅ Complete ⭐ NEW! |
| **Support Classes** | 5/5 | 100% | ✅ Complete |
| **Integration Tests** | 0/3 | 0% | ❌ Not Started |
| **Performance Tests** | 0/3 | 0% | ❌ Not Started |
| **CLI** | 0/1 | 0% | ❌ Not Started |

**Overall Completion: ~80%** 🎯

---

## 🤝 Contributing

Interested in helping? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

High-priority areas where contributions are welcome:
1. Implementing missing Dgraph operations
2. Writing integration tests
3. Creating examples
4. Performance benchmarking

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Last Updated:** 2025-11-18
**Maintainer:** @c4ffein (with AI pair-programming assistance from Claude)

**Latest Achievement:** 🎉 Phase 1 COMPLETE - All Scotch distributed graph operations implemented!
