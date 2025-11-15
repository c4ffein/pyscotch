# PT-Scotch Distributed Graph Tests

All `test_scotch_dgraph_*.c` tests are **distributed graph (PT-Scotch) tests** that require MPI (Message Passing Interface).

## Why These Tests Are Not Ported

These tests use PT-Scotch's distributed graph API (`SCOTCH_Dgraph`) which requires:

1. **MPI Runtime**: All tests call `MPI_Init()` or `MPI_Init_thread()` at startup
2. **Multiple Processes**: Tests must be run with `mpirun -n <nprocs>`
3. **Distributed Data Structures**: Graphs are split across MPI processes
4. **Collective Operations**: Functions require synchronization across all processes

## Tests in This Category

- `test_scotch_dgraph_band.c` - Distributed graph banding
- `test_scotch_dgraph_check.c` - Distributed graph checking
- `test_scotch_dgraph_coarsen.c` - Distributed graph coarsening
- `test_scotch_dgraph_grow.c` - Distributed graph growing
- `test_scotch_dgraph_induce.c` - Distributed graph induction
- `test_scotch_dgraph_redist.c` - Distributed graph redistribution

## Why MPI Tests Are Challenging for PyScotch

1. **MPI Initialization**: Python MPI bindings (mpi4py) must initialize MPI before any PT-Scotch calls
2. **Process Management**: Tests require multiple Python processes coordinating via MPI
3. **Data Distribution**: Graph data must be manually distributed across processes
4. **Testing Infrastructure**: pytest doesn't natively support MPI-based tests (requires pytest-mpi plugin)
5. **CI/CD Complexity**: Requires MPI runtime in CI environment

## Potential Future Work

If PT-Scotch MPI testing becomes a priority:

1. Use `mpi4py` for Python MPI bindings
2. Use `pytest-mpi` plugin for MPI-aware testing
3. Create helper functions for distributing test graphs across MPI ranks
4. Set up CI environment with MPI support (e.g., OpenMPI or MPICH)

For now, PyScotch focuses on sequential Scotch testing. Distributed graph functionality
is available through the PT-Scotch bindings but requires users to handle MPI initialization
and data distribution in their own applications.
