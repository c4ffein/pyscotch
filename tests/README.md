# PyScotch Test Suite

Test suite organized into three main categories:

## Directory Structure

```
tests/
├── pyscotch_base/          # PyScotch-specific tests
│   ├── test_graph.py
│   ├── test_int_sizes.py
│   ├── test_mapping_ordering.py
│   ├── test_multivariant_parametrized.py
│   └── test_scotch_compat.py
│
├── scotch_ports/           # Direct ports from Scotch C test suite
│   ├── test_scotch_graph_color.py
│   ├── test_scotch_graph_coarsen.py
│   ├── test_scotch_dgraph_*.py     (PT-Scotch parallel tests)
│   ├── test_common_*.py
│   └── ...                         (25 test files total)
│
└── hypothesis/             # Property-based tests (future)
    └── README.md
```

## Test Categories

### 1. pyscotch_base/ - PyScotch Specific Tests

Tests for PyScotch Python bindings and multi-variant support:

- **test_graph.py**: Basic Graph class tests
- **test_mapping_ordering.py**: Mapping and Ordering classes
- **test_int_sizes.py**: 32/64-bit integer size handling
- **test_multivariant_parametrized.py**: Multi-variant loading (32/64 × seq/par)
- **test_scotch_compat.py**: Basic compatibility with Scotch C API

**Status**: ✅ **97/97 passing (100%)**

### 2. scotch_ports/ - Scotch C Test Suite Ports

Direct ports from `external/scotch/src/check/` mirroring the exact structure for easy tracking:

#### Sequential Graph Tests
- `test_scotch_graph_color.py` - Graph coloring
- `test_scotch_graph_coarsen.py` - Graph coarsening
- `test_scotch_graph_diam.py` - Diameter computation
- `test_scotch_graph_dump.py` - Graph dumping
- `test_scotch_graph_induce.py` - Subgraph induction
- `test_scotch_graph_map_copy.py` - Mapping copy
- `test_scotch_graph_part_ovl.py` - Partitioning with overlap

#### Parallel/Distributed (PT-Scotch) Tests
- `test_scotch_dgraph_band.py` - Distributed band operations
- `test_scotch_dgraph_check.py` - Distributed graph checking
- `test_scotch_dgraph_coarsen.py` - Distributed coarsening
- `test_scotch_dgraph_grow.py` - Distributed growing
- `test_scotch_dgraph_induce.py` - Distributed induction
- `test_scotch_dgraph_redist.py` - Distributed redistribution

#### Architecture & Strategy Tests
- `test_scotch_arch_deco.py` - Architecture decomposition
- `test_scotch_context.py` - Context management
- `test_strat_par.py` - Parallel strategies

#### Mesh Tests
- `test_scotch_mesh_graph.py` - Mesh to graph conversion

#### Utility Tests
- `test_common_file_compress.py` - File compression
- `test_common_random.py` - Random number generation
- `test_common_thread.py` - Threading utilities
- `test_fibo.py` - Fibonacci heap

#### Compatibility Layer Tests
- `test_libesmumps.py` - Esmumps compatibility
- `test_libmetis.py` - METIS compatibility
- `test_libmetis_dual.py` - METIS dual graph
- `test_multilib.py` - Multi-library support

**Status**: 🚧 **Skeleton files created (all raise NotImplementedError)**

**Porting Progress**: 0/24 tests ported

### 3. hypothesis/ - Property-Based Tests

Future home for property-based tests using Hypothesis framework.

**Status**: 📋 **Planned**

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run only PyScotch base tests (all passing)
pytest tests/pyscotch_base/ -v

# Run only Scotch ports (will show NotImplementedError)
pytest tests/scotch_ports/ -v

# Collect test inventory without running
pytest tests/ --collect-only
```

## Current Status

- **pyscotch_base**: ✅ 97/97 passing (100%)
- **scotch_ports**: 🚧 24 skeleton files created, 0 ported
- **hypothesis**: 📋 Planned

## Contributing

When porting tests from Scotch C test suite to `scotch_ports/`:

1. Keep the same file name: `test_scotch_*.c` → `test_scotch_*.py`
2. Reference the C file in docstring: `Ported from: external/scotch/src/check/...`
3. Maintain test structure and intent from original C code
4. Add explicit variant fixture (sequential vs PT-Scotch parallel)
5. Remove `raise NotImplementedError` once ported

This structure makes it easy to track which Scotch tests have been ported!
