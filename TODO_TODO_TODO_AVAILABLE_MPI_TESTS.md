# Available PT-Scotch MPI Tests

This document catalogs all MPI-based tests available in the Scotch test suite that could be ported to PyScotch.

## Test Inventory

Based on `external/scotch/src/check/Makefile` and test files:

| Test File | Function Tested | Process Count | Test Graphs | Status |
|-----------|----------------|---------------|-------------|--------|
| `test_scotch_dgraph_check.c` | `SCOTCH_dgraphCheck()` | 3 | bump.grf, bump_b100000.grf | ✅ **PORTED** |
| `test_scotch_dgraph_band.c` | `SCOTCH_dgraphBand()` | 3 | bump.grf, bump_b100000.grf | ❌ Not ported |
| `test_scotch_dgraph_coarsen.c` | `SCOTCH_dgraphCoarsen()` | 3 | bump.grf, bump_b100000.grf, m4x4_b1.grf | ❌ Not ported |
| `test_scotch_dgraph_grow.c` | `SCOTCH_dgraphGrow()` | 3 | bump.grf, bump_b100000.grf | ❌ Not ported |
| `test_scotch_dgraph_induce.c` | `SCOTCH_dgraphInducePart()` | 3 | bump.grf, bump_b100000.grf | ❌ Not ported |
| `test_scotch_dgraph_redist.c` | `SCOTCH_dgraphRedist()` | 3 | bump.grf, bump_b100000.grf | ❌ Not ported |

**Total**: 1/6 tests ported (16.7%)

## Test Details

### ✅ dgraph_check - Graph Validation

**Status**: ✅ Ported in `tests/scotch_ports_mpi/mpi_scripts/dgraph_check_real.py`

**What it does**: Loads a distributed graph and validates its internal consistency
- Tests: `SCOTCH_dgraphLoad()`, `SCOTCH_dgraphCheck()`
- Returns: Success if graph structure is valid

**PyScotch API Coverage**:
- ✅ `Dgraph.load()` - implemented
- ✅ `Dgraph.check()` - implemented

---

### ❌ dgraph_band - Band Graph Extraction

**What it does**: Computes a band graph around a separator (used in graph partitioning)
- Tests: `SCOTCH_dgraphLoad()`, `SCOTCH_dgraphBand()`
- Input: Graph file + separator map file
- Output: Band graph structure

**PyScotch API Coverage**:
- ✅ `Dgraph.load()` - implemented
- ❌ `Dgraph.band()` - **NOT IMPLEMENTED**

**Implementation Needed**: Would require wrapping `SCOTCH_dgraphBand()`

---

### ❌ dgraph_coarsen - Graph Coarsening

**What it does**: Creates a coarsened version of a distributed graph (merges similar vertices)
- Tests: `SCOTCH_dgraphLoad()`, `SCOTCH_dgraphCoarsen()`, multiple coarsening passes
- Used in: Multilevel graph algorithms
- Output: Coarsened graph + statistics

**PyScotch API Coverage**:
- ✅ `Dgraph.load()` - implemented
- ❌ `Dgraph.coarsen()` - **NOT IMPLEMENTED**

**Implementation Needed**: Would require wrapping `SCOTCH_dgraphCoarsen()`

---

### ❌ dgraph_grow - Region Growing

**What it does**: Grows a region from seed vertices (k-way partitioning building block)
- Tests: `SCOTCH_dgraphLoad()`, `SCOTCH_dgraphGrow()`
- Input: Graph file + seed partition
- Output: Grown partition map file

**PyScotch API Coverage**:
- ✅ `Dgraph.load()` - implemented
- ❌ `Dgraph.grow()` - **NOT IMPLEMENTED**

**Implementation Needed**: Would require wrapping `SCOTCH_dgraphGrow()`

---

### ❌ dgraph_induce - Subgraph Induction

**What it does**: Extracts an induced subgraph from a distributed graph based on a partition
- Tests: `SCOTCH_dgraphLoad()`, `SCOTCH_dgraphInducePart()`
- Creates subgraph containing only vertices from a specific partition
- Validates induced subgraph structure

**PyScotch API Coverage**:
- ✅ `Dgraph.load()` - implemented
- ❌ `Dgraph.induce_part()` - **NOT IMPLEMENTED**

**Implementation Needed**: Would require wrapping `SCOTCH_dgraphInducePart()`

---

### ❌ dgraph_redist - Graph Redistribution

**What it does**: Redistributes a distributed graph across MPI processes (load balancing)
- Tests: `SCOTCH_dgraphLoad()`, `SCOTCH_dgraphRedist()`
- Creates new distribution of graph data
- Validates redistributed graph

**PyScotch API Coverage**:
- ✅ `Dgraph.load()` - implemented
- ❌ `Dgraph.redist()` - **NOT IMPLEMENTED**

**Implementation Needed**: Would require wrapping `SCOTCH_dgraphRedist()`

---

## Implementation Priority

### Can Port Immediately (only test code needed):
1. ✅ **dgraph_check** - Already done!

### Requires New PyScotch Methods:
All other tests require implementing new Dgraph methods. Suggested priority:

1. **dgraph_coarsen** - Core multilevel algorithm component
2. **dgraph_grow** - Core partitioning algorithm component
3. **dgraph_redist** - Load balancing functionality
4. **dgraph_induce** - Subgraph extraction
5. **dgraph_band** - Separator analysis

## Test Data Files

Located in `external/scotch/src/check/data/`:

- **bump.grf** - Standard test graph (used by all tests)
- **bump_b100000.grf** - Variant with baseval=100000
- **m4x4_b1.grf** - Small 4x4 mesh with baseval=1
- Various other graphs for specific tests

## Next Steps

To port additional MPI tests:

1. **Choose a test** from the list above
2. **Implement the PyScotch method** (e.g., `Dgraph.band()`)
3. **Create MPI script** in `tests/scotch_ports_mpi/mpi_scripts/`
4. **Add pytest orchestrator** in `tests/scotch_ports_mpi/test_dgraph.py`
5. **Test with same data** as Scotch (e.g., bump.grf)
6. **Update this document** to mark as ported

## References

- Scotch Makefile: `external/scotch/src/check/Makefile`
- Scotch test files: `external/scotch/src/check/test_scotch_dgraph_*.c`
- Our MPI tests: `tests/scotch_ports_mpi/`
