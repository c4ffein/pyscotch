# Scotch Test Porting Status

Tracking progress of porting Scotch C tests to Python.

## Legend
- ✅ Ported and working
- 🚧 In progress
- ⏳ Not started (skeleton with NotImplementedError)
- ⏭️  Skipped (already covered in pyscotch_base/)

## Sequential Graph Tests

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_graph_color.c | test_scotch_graph_color.py | ⏳ | Graph coloring algorithm |
| test_scotch_graph_coarsen.c | test_scotch_graph_coarsen.py | ⏳ | Multilevel coarsening |
| test_scotch_graph_diam.c | test_scotch_graph_diam.py | ⏳ | Diameter computation |
| test_scotch_graph_dump.c | test_scotch_graph_dump.py | ⏳ | Internal structure dumping |
| test_scotch_graph_induce.c | test_scotch_graph_induce.py | ⏳ | Subgraph induction |
| test_scotch_graph_map_copy.c | test_scotch_graph_map_copy.py | ⏳ | Mapping copy operations |
| test_scotch_graph_part_ovl.c | test_scotch_graph_part_ovl.py | ⏳ | Partitioning with overlap |

## Parallel/Distributed (PT-Scotch) Tests

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_dgraph_band.c | test_scotch_dgraph_band.py | ⏳ | Band operations |
| test_scotch_dgraph_check.c | test_scotch_dgraph_check.py | ⏳ | Distributed graph checking |
| test_scotch_dgraph_coarsen.c | test_scotch_dgraph_coarsen.py | ⏳ | Distributed coarsening |
| test_scotch_dgraph_grow.c | test_scotch_dgraph_grow.py | ⏳ | Distributed growing |
| test_scotch_dgraph_induce.c | test_scotch_dgraph_induce.py | ⏳ | Distributed induction |
| test_scotch_dgraph_redist.c | test_scotch_dgraph_redist.py | ⏳ | Redistribution |

## Architecture & Strategy

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_arch.c | (in pyscotch_base) | ⏭️ | Basic arch tests covered |
| test_scotch_arch_deco.c | test_scotch_arch_deco.py | ⏳ | Architecture decomposition |
| test_scotch_context.c | test_scotch_context.py | ⏳ | Context management |
| test_strat_seq.c | (in pyscotch_base) | ⏭️ | Basic strategy tests covered |
| test_strat_par.c | test_strat_par.py | ⏳ | Parallel strategies |

## Mesh

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_scotch_mesh_graph.c | test_scotch_mesh_graph.py | ⏳ | Mesh to graph conversion |

## Utilities

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_common_file_compress.c | test_common_file_compress.py | ⏳ | File compression |
| test_common_random.c | test_common_random.py | ⏳ | Random number gen |
| test_common_thread.c | test_common_thread.py | ⏳ | Threading utilities |
| test_fibo.c | test_fibo.py | ⏳ | Fibonacci heap |

## Compatibility Layers

| C File | Python File | Status | Notes |
|--------|-------------|--------|-------|
| test_libesmumps.c | test_libesmumps.py | ⏳ | Esmumps compatibility |
| test_libmetis.c | test_libmetis.py | ⏳ | METIS compatibility |
| test_libmetis_dual.c | test_libmetis_dual.py | ⏳ | METIS dual graph |
| test_multilib.c | test_multilib.py | ⏳ | Multi-library support |

## Overall Progress

**Total**: 0/24 ported (0%)

- ✅ Ported: 0
- 🚧 In progress: 0
- ⏳ Not started: 24
- ⏭️ Skipped (covered elsewhere): 4

## Suggested Porting Order

Start with simpler tests to build momentum:

1. **Easy wins** (basic operations):
   - test_scotch_graph_dump.py - just dumping structure
   - test_scotch_context.py - context init/exit
   - test_common_random.py - RNG utilities

2. **Core graph operations**:
   - test_scotch_graph_induce.py - subgraph operations
   - test_scotch_graph_color.py - coloring algorithm
   - test_scotch_graph_coarsen.py - coarsening

3. **Advanced features**:
   - test_scotch_graph_diam.py - diameter computation
   - test_scotch_graph_map_copy.py - mapping operations
   - test_scotch_mesh_graph.py - mesh support

4. **Parallel/distributed** (requires MPI understanding):
   - test_scotch_dgraph_*.py - all dgraph tests

5. **Compatibility layers** (lower priority):
   - test_lib*.py - METIS/Esmumps compatibility

## How to Port a Test

1. Read the C file in `external/scotch/src/check/`
2. Understand what it's testing
3. Open the skeleton Python file in `tests/scotch_ports/`
4. Replace `raise NotImplementedError` with actual test code
5. Run `pytest tests/scotch_ports/test_yourfile.py -v`
6. Update this file's status from ⏳ to ✅
7. Celebrate! 🎉

Let's get porting! 🚀
