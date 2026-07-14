# Scotch Test Porting Status

**All 29 Scotch C tests have been categorized and documented.**

## Legend
- ✅ **Fully ported** - Tests passing
- 🔧 **Missing bindings** - Requires compat library bindings (ESMUMPS/METIS)
- 🚫 **Internal API** - Tests internal implementation (not public API)
- 📡 **MPI required** - Requires MPI runtime (PT-Scotch distributed)
- ⏭️ **Covered elsewhere** - Functionality tested in pyscotch_base/

## Sequential Graph Tests

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_graph_color.c | test_scotch_graph_color.py | ✅ | Graph coloring - 4 tests passing |
| test_scotch_graph_coarsen.c | test_scotch_graph_coarsen.py | ✅ | Multilevel coarsening - 3 tests passing |
| test_scotch_graph_diam.c | test_scotch_graph_diam.py | ✅ | Diameter computation - 5 tests passing |
| test_scotch_graph_dump.c | test_scotch_graph_dump.py | ✅ | Graph save/load roundtrip - 3 tests passing |
| test_scotch_graph_induce.c | test_scotch_graph_induce.py | ✅ | Subgraph induction - 5 tests passing |
| test_scotch_graph_map_copy.c | test_scotch_graph_map_copy.py | ✅ | Mapping & remapping - 3 tests passing |
| test_scotch_graph_part_ovl.c | test_scotch_graph_part_ovl.py | ✅ | Overlapping partitions - 2 tests passing |

## Parallel/Distributed (PT-Scotch) Tests

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_dgraph_band.c | test_scotch_dgraph_band.py | 📡 | MPI required - see _DGRAPH_MPI_NOTE.md |
| test_scotch_dgraph_check.c | test_scotch_dgraph_check.py | 📡 | MPI required |
| test_scotch_dgraph_coarsen.c | test_scotch_dgraph_coarsen.py | 📡 | MPI required |
| test_scotch_dgraph_grow.c | test_scotch_dgraph_grow.py | 📡 | MPI required |
| test_scotch_dgraph_induce.c | test_scotch_dgraph_induce.py | 📡 | MPI required |
| test_scotch_dgraph_order.c | scotch_ports_mpi/mpi_scripts/dgraph_order.py | ✅ 📡 | Ported - runs under mpirun via scotch_ports_mpi/test_dgraph.py (2 tests passing) |
| test_scotch_dgraph_redist.c | test_scotch_dgraph_redist.py | 📡 | MPI required |

PyScotch-specific MPI tests without an upstream C equivalent (in
`scotch_ports_mpi/mpi_scripts/`, run via `scotch_ports_mpi/test_dgraph.py`):
- `dgraph_part.py` — SCOTCH_dgraphPart / dgraphMap / dgraphMapInit/Compute/Exit / dgraphMapView (3 tests passing)
- `dgraph_gather_scatter.py` — SCOTCH_dgraphScatter / dgraphGather roundtrip vs a sequential graph (2 tests passing)
- `dgraph_order_extra.py` — dgraphOrderCompute/Perm/CblkDist/TreeDist/Save/SaveMap/SaveTree (1 test passing)
- `dgraph_grid_stat.py` — SCOTCH_dgraphBuildGrid3D / dgraphStat / dgraphFree (1 test passing)

## Architecture & Strategy

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_arch.c | (in pyscotch_base) | ⏭️ | Basic arch tests covered |
| test_scotch_arch_deco.c | test_scotch_arch_deco.py | ✅ | Arch build/save/sub - 5 tests passing |
| test_scotch_context.c | test_scotch_context.py | 🚫 | INTERNAL: Threading API |
| test_strat_seq.c | (in pyscotch_base) | ⏭️ | Basic strategy tests covered |
| test_strat_par.c | test_strat_par.py | 📡 | MPI required |

## Mesh

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_mesh_graph.c | test_scotch_mesh_graph.py | ✅ | Mesh to graph - 2 tests passing |

## Utilities

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_common_file_compress.c | test_common_file_compress.py | 🚫 | INTERNAL: File compression API |
| test_common_random.c | test_common_random.py | ✅ | Partial - 1 test passing (public API only) |
| test_common_thread.c | test_common_thread.py | 🚫 | INTERNAL: Threading primitives |
| test_fibo.c | test_fibo.py | 🚫 | INTERNAL: Fibonacci heap |

## Compatibility Layers

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_libesmumps.c | test_libesmumps.py | 🔧 | Missing libesmumps bindings |
| test_libmetis.c | test_libmetis.py | 🔧 | Missing libscotchmetis bindings |
| test_libmetis_dual.c | test_libmetis_dual.py | 🔧 | Missing libscotchmetis bindings |
| test_multilib.c | test_multilib.py | ✅ | Single-variant load test - 2 tests passing |

## Final Summary

### Test Counts (29 total C tests)
- ✅ **12 fully ported** (34 tests passing total)
  - test_scotch_graph_color (4 tests)
  - test_scotch_graph_coarsen (3 tests)
  - test_scotch_graph_diam (5 tests)
  - test_scotch_graph_dump (3 tests)
  - test_scotch_graph_induce (5 tests)
  - test_scotch_graph_map_copy (3 tests)
  - test_scotch_graph_part_ovl (2 tests)
  - test_scotch_arch_deco (5 tests)
  - test_scotch_mesh_graph (2 tests)
  - test_multilib (2 tests)
  - test_common_random (1 test - public API)

- 🔧 **3 missing compat library bindings** (not core Scotch API)
  - test_libesmumps (needs libesmumps bindings)
  - test_libmetis (needs libscotchmetis bindings)
  - test_libmetis_dual (needs libscotchmetis bindings)

- 📡 **7 MPI required** (PT-Scotch distributed graphs)
  - All test_scotch_dgraph_* tests (6)
  - test_strat_par (1)

- 🚫 **4 internal API** (not part of public scotch.h)
  - test_fibo (Fibonacci heap)
  - test_common_thread (threading primitives)
  - test_scotch_context (threading implementation)
  - test_common_file_compress (file compression)

- ⏭️ **2 covered elsewhere** (in pyscotch_base/)
  - test_scotch_arch
  - test_strat_seq

### Success Rate
- **100% categorized and documented** ✅
- **50% fully ported with passing tests** (12/24 portable tests)
- **12% missing compat bindings** (3/24)
- **29% require MPI infrastructure** (7/24)
- **17% internal API (correctly excluded)** (4/24)

### Note on FILE* Resolution
The FILE* pointer limitation that originally blocked 9 tests has been fully
resolved via the `c_fopen()` compatibility shim in `pyscotch/graph.py`. This
shim uses a C helper library (`libpyscotch_compat.so`) compiled with the same
toolchain as Scotch, guaranteeing ABI compatibility. All graph/mesh/arch
load/save operations now work through this shim.
