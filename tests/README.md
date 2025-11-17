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
├── scotch_ports_mpi/       # MPI orchestration tests (PT-Scotch)
│   ├── mpi_scripts/        # Standalone MPI test programs
│   │   ├── dgraph_init.py
│   │   ├── dgraph_build.py
│   │   ├── dgraph_check.py
│   │   └── dgraph_check_real.py
│   └── test_dgraph.py      # Pytest orchestrator
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

### 3. scotch_ports_mpi/ - PT-Scotch MPI Tests

Direct ports of PT-Scotch distributed graph tests, following Scotch's MPI testing pattern.

#### Scotch's MPI Testing Approach

Scotch uses a proven two-layer pattern for MPI tests:

1. **Standalone MPI executables** - Each test is a complete program:
   ```c
   // test_scotch_dgraph_coarsen.c
   int main(int argc, char *argv[]) {
       MPI_Init(&argc, &argv);

       SCOTCH_dgraphInit(&dgraph, MPI_COMM_WORLD);
       // Test logic...

       MPI_Finalize();
       return 0;  // 0 = success, non-zero = failure
   }
   ```

2. **Makefile orchestrates mpirun** - Build system spawns processes:
   ```make
   EXECP3 = mpirun -n 3

   check_scotch_dgraph_coarsen:
       $(EXECP3) ./test_scotch_dgraph_coarsen data/bump.grf
   ```

#### Our Python Equivalent

We mirror this exact pattern:

**Standalone MPI scripts** (tests/scotch_ports_mpi/mpi_scripts/):
```python
# dgraph_check_real.py
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph

mpi.init()
# Test logic using PT-Scotch...
dgraph = Dgraph()
dgraph.load(graph_file)
is_valid = dgraph.check()
mpi.finalize()
```

**Pytest orchestrates mpirun** (tests/scotch_ports_mpi/test_dgraph.py):
```python
def test_dgraph_check_real_bump():
    """Pytest spawns mpirun subprocess."""
    result = subprocess.run(
        ["mpirun", "-np", "2", "python",
         "tests/mpi_scripts/dgraph_check_real.py",
         "external/scotch/src/check/data/bump.grf"],
        capture_output=True
    )
    assert result.returncode == 0
```

#### Key Design Points

- ✅ Each MPI script is standalone (not a test framework)
- ✅ mpirun called by orchestrator (pytest), not by scripts themselves
- ✅ Scripts return 0 for success, non-zero for failure
- ✅ Different tests use different process counts (-np 2, 3, 4, etc.)
- ✅ Direct correspondence with Scotch C tests

#### Ported Tests

- **dgraph_init.py** - Distributed graph initialization
- **dgraph_build.py** - Manual graph construction (CSR format)
- **dgraph_check.py** - Empty graph validation
- **dgraph_check_real.py** - Real graph validation (bump.grf)

**Status**: ✅ **4/4 MPI tests passing**

### 4. hypothesis/ - Property-Based Tests

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

# Run only MPI tests (requires mpirun)
pytest tests/scotch_ports_mpi/ -v

# Run specific MPI test with verbose output
pytest tests/scotch_ports_mpi/test_dgraph.py::TestDgraph::test_dgraph_check_real_bump -v -s

# Collect test inventory without running
pytest tests/ --collect-only
```

## Current Status

- **pyscotch_base**: ✅ 97/97 passing (100%)
- **scotch_ports**: 🚧 24 skeleton files created, 0 ported
- **scotch_ports_mpi**: ✅ 4/4 MPI tests passing (100%)
- **hypothesis**: 📋 Planned

**Total**: ✅ 101 tests passing

## Contributing

### Porting Sequential Tests (scotch_ports/)

When porting tests from Scotch C test suite to `scotch_ports/`:

1. Keep the same file name: `test_scotch_*.c` → `test_scotch_*.py`
2. Reference the C file in docstring: `Ported from: external/scotch/src/check/...`
3. Maintain test structure and intent from original C code
4. Add explicit variant fixture (sequential vs PT-Scotch parallel)
5. Remove `raise NotImplementedError` once ported

### Porting MPI Tests (scotch_ports_mpi/)

When porting PT-Scotch MPI tests:

1. **Create standalone MPI script** in `mpi_scripts/`:
   - Use `mpi.init()` / `mpi.finalize()`
   - Return exit code 0 for success, non-zero for failure
   - Include docstring with reference to original C test

2. **Create pytest orchestrator** in `test_dgraph.py`:
   - Use `subprocess.run()` with `mpirun -np N`
   - Assert on return code and output
   - Match process count from original Makefile

3. **Use same test data** as Scotch:
   - Reference graphs from `external/scotch/src/check/data/`
   - Keep same baseval and flags

This structure makes it easy to track which Scotch tests have been ported!
