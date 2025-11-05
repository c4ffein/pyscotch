# PyScotch Test Results

## Summary
After building ptscotch from the cloned scotch repository, here are the test results:

**Total Tests: 31**
- ✓ **PASSED: 23** (74.2%)
- ✗ **FAILED: 0** (0%)
- 💥 **CRASHED: 8** (25.8%)

---

## ✓ Passing Tests (23)

### Basic Functionality (3)
- `test_graph::TestGraph::test_graph_creation` - Graph object creation works
- `test_graph::TestGraph::test_mapping_class` - Mapping class integration works
- `test_graph::TestGraph::test_mapping_unbalanced` - Unbalanced mapping works

### Strategy Tests (2)
- `test_graph::TestStrategy::test_strategy_creation` - Strategy creation works
- `test_graph::TestStrategy::test_strategy_methods` - Strategy configuration works

### Mapping Tests (9)
- `test_mapping_ordering::TestMapping::test_mapping_creation` - Create mapping from array
- `test_mapping_ordering::TestMapping::test_mapping_num_partitions` - Get number of partitions
- `test_mapping_ordering::TestMapping::test_mapping_get_partition` - Get vertices in partition
- `test_mapping_ordering::TestMapping::test_mapping_balance_perfect` - Perfect balance calculation
- `test_mapping_ordering::TestMapping::test_mapping_balance_unbalanced` - Unbalanced calculation
- `test_mapping_ordering::TestMapping::test_mapping_get_partition_sizes` - Get partition sizes
- `test_mapping_ordering::TestMapping::test_mapping_getitem` - Array-like indexing
- `test_mapping_ordering::TestMapping::test_mapping_save_load` - Save/load to file
- `test_mapping_ordering::TestMapping::test_mapping_repr` - String representation

### Ordering Tests (9)
- `test_mapping_ordering::TestOrdering::test_ordering_creation` - Create ordering from array
- `test_mapping_ordering::TestOrdering::test_ordering_with_inverse` - Create with inverse permutation
- `test_mapping_ordering::TestOrdering::test_ordering_auto_inverse` - Auto-compute inverse
- `test_mapping_ordering::TestOrdering::test_ordering_apply` - Apply ordering to array
- `test_mapping_ordering::TestOrdering::test_ordering_apply_inverse` - Apply inverse ordering
- `test_mapping_ordering::TestOrdering::test_ordering_roundtrip` - Verify roundtrip consistency
- `test_mapping_ordering::TestOrdering::test_ordering_getitem` - Array-like indexing
- `test_mapping_ordering::TestOrdering::test_ordering_save_load` - Save/load to file
- `test_mapping_ordering::TestOrdering::test_ordering_repr` - String representation

---

## 💥 Crashed Tests (8 - Segfault Issues)

These tests cause segmentation faults when calling into the Scotch C library:

1. `test_graph::TestGraph::test_graph_from_edges` - Create graph from edge list
2. `test_graph::TestGraph::test_graph_build` - Build graph from arrays
3. `test_graph::TestGraph::test_graph_check` - Graph consistency checking
4. `test_graph::TestGraph::test_graph_partition` - Graph partitioning
5. `test_graph::TestGraph::test_graph_partition_with_strategy` - Partitioning with strategy
6. `test_graph::TestGraph::test_graph_order` - Graph ordering
7. `test_graph::TestGraph::test_graph_size` - Get graph size (if exists)
8. `test_graph::TestGraph::test_graph_data` - Get graph data (if exists)

### Likely Causes of Crashes:
1. **API Mismatch**: The ctypes bindings may not match the actual C library API in scotch 7.0
2. **Memory Layout**: Structure sizes or field ordering might differ
3. **Pointer Handling**: Issues with how numpy arrays are passed to C functions
4. **Initialization**: Graph structure might not be properly initialized before use

---

## Analysis

### What Works ✓
- **Library Loading**: The scotch shared library loads successfully
- **Python Wrapper Classes**: All Python-only functionality (Mapping, Ordering) works perfectly
- **Strategy Objects**: Strategy creation and configuration works
- **Basic Graph Creation**: Empty graph objects can be created

### What Doesn't Work 💥
- **Graph Building**: Any operation that actually builds graph structure crashes
- **Scotch C API Calls**: Most calls into libscotch.so cause segfaults
- **Graph Operations**: Partitioning, ordering, checking all crash

### Next Steps to Fix Crashes:
1. Verify structure definitions match scotch 7.0 API
2. Check SCOTCH_Num and SCOTCH_Idx type sizes
3. Add debug logging to see which C function call fails
4. Review ctypes argument/return type declarations
5. Compare with scotch example C programs
6. May need to use dummysizes output to get correct structure sizes
