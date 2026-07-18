# Tutorial: Parallel PyScotch (PT-Scotch)

Everything about running PyScotch distributed: what PT-Scotch needs, how to
launch it, and what every failure on the way there means. Installation of the
parallel pieces is covered in [Installing PyScotch](04_installing_pyscotch.html);
this page is about *using* them.

## What "parallel" means here

Sequential Scotch partitions a graph that fits in one process. PT-Scotch
distributes the graph itself: each MPI rank holds a slice (a `Dgraph`), and
partitioning/ordering run cooperatively across ranks. You want it when the
graph is too big for one node, or when the rest of your application is already
MPI-parallel and the graph is born distributed.

Two things must be true before any of this works, and both are checked by
`pyscotch doctor`:

1. A **PT-Scotch library** is loadable (`pyscotch scotch build 7.0.11 --parallel --use`
   builds one, no root needed).
2. `PYSCOTCH_PARALLEL=1` is set **before `import pyscotch`** — the library is
   chosen at import time, so setting it later in the program has no effect.

```bash
PYSCOTCH_PARALLEL=1 pyscotch doctor    # verifies the full parallel stack
```

## Launching: mpirun, and why we don't wrap it

PyScotch deliberately has **no launcher of its own** — you run parallel scripts
with the standard MPI launcher, exactly like any mpi4py/PETSc/FEniCS program:

```bash
PYSCOTCH_PARALLEL=1 PYSCOTCH_INT_SIZE=64 mpirun -n 4 python your_script.py
```

This is the convention of the whole Python-MPI ecosystem, and it is what makes
PyScotch composable with it: on a cluster the launcher is site-specific (`srun`
under SLURM, vendor `mpiexec`s, …), schedulers integrate at that level, and any
wrapper we shipped would have to be bypassed there anyway. mpi4py itself
follows the same rule — its `python -m mpi4py your_script.py` helper still runs
*under* `mpiexec`; it only adds abort-on-unhandled-exception so one crashed
rank cannot deadlock the others. That tip is worth using:

```bash
PYSCOTCH_PARALLEL=1 mpirun -n 4 python -m mpi4py your_script.py
```

If `mpirun` refuses because you ask for more ranks than cores (common in CI
and on laptops), pass `--oversubscribe` — and PyScotch's own MPI-touching
tests honor `PYSCOTCH_MPI_OVERSUBSCRIBE=1` for the same purpose.

## No mpirun? That works too

An MPI program started without a launcher is a valid **1-rank** job ("singleton
init"). So this runs fine:

```bash
PYSCOTCH_PARALLEL=1 python your_script.py     # 1 rank, no launcher
```

You get no parallelism, but you get something better during development: the
whole Dgraph API under a plain debugger, no launcher in the way. Move to
`mpirun -n N` only when you actually want N ranks.

## Communicators

The recommended route is mpi4py — hand any of its communicators to `Dgraph`,
not just `COMM_WORLD`:

```python
from mpi4py import MPI               # runs MPI_Init on import
from pyscotch import Dgraph

comm = MPI.COMM_WORLD                 # or comm.Split(...), comm.Dup(), ...
dg = Dgraph(comm=comm)
dg.build_grid_3d(8, 8, 8)             # each rank holds a slice
part = dg.part(4)                     # local assignments on this rank
dg.exit()
```

PyScotch passes mpi4py's native `MPI_Comm` handle straight to Scotch, so both
share one MPI runtime. Without mpi4py, the bundled zero-dependency
`pyscotch.mpi` wrapper drives `MPI_COMM_WORLD` — but then *you* must call
`pyscotch.mpi.init()` before creating a `Dgraph`.

A complete, runnable tour — sequential and parallel in one script, with clean
messages when a piece is missing — lives in `examples/hello_pyscotch.py`:

```bash
python examples/hello_pyscotch.py                                        # sequential
PYSCOTCH_PARALLEL=1 PYSCOTCH_INT_SIZE=64 mpirun -n 2 \
    python examples/hello_pyscotch.py                                    # parallel
```

## When it goes wrong

Every one of these is an *expected*, tested failure with a precise meaning
(they are locked byte-for-byte in PyScotch's golden-master CI):

| You see | It means | Fix |
|---|---|---|
| `FileNotFoundError: No Scotch library found ...` at import | `PYSCOTCH_PARALLEL=1` is set but no PT-Scotch build is available anywhere | `pyscotch scotch build 7.0.11 --parallel --use` |
| `RuntimeError: Dgraph requires PT-Scotch (parallel variant)` | The *sequential* library loaded — `PYSCOTCH_PARALLEL=1` wasn't set before import | put the env var on the command line |
| `RuntimeError: MPI must be initialized before creating Dgraph` | You used the bundled wrapper without `mpi.init()` | call `pyscotch.mpi.init()`, or pass an mpi4py communicator |
| `mpirun ... not enough slots` | more ranks than cores | `mpirun --oversubscribe`, `PYSCOTCH_MPI_OVERSUBSCRIBE=1` |

When in doubt, start with the doctor — it reports the loaded backend, the MPI
implementation, and the exact command that fixes whatever is missing:

```bash
PYSCOTCH_PARALLEL=1 pyscotch doctor
```

## Reproducibility across ranks

Scotch's pseudo-random generator state affects partitioning, and PyScotch
follows Scotch's own semantics exactly: **the PRNG stream carries across
calls, and nothing resets it implicitly.** A fresh process starts from the
seed, so single-operation runs are reproducible whenever the library was
compiled with `COMMON_RANDOM_FIXED_SEED` (seed = 1) — which is the norm: 31 of
Scotch's 32 upstream `Make.inc` templates set it, and `pyscotch scotch build`
does too. Without that flag the seed is `time(NULL)` and no run is
reproducible. For repeated in-process calls, choose explicitly:

```python
pyscotch.random_reset()      # before an operation: make this call reproducible
part = dg.part(4)            # ... or pass reset_random=True for the same effect
```

Ranks stay in lockstep **by default**: the seed ignores the process rank, so
all ranks draw identical sequences. Both escape hatches are deliberate,
user-invoked features, mirroring the C API one-to-one:

- `SCOTCH_randomProc(rank)` folds a process number into the seed when you
  *want* decorrelated ranks;
- `Context.random_clone()` gives a context its own private stream — which a
  global `random_reset()` then deliberately does *not* touch.

Leave the stream running when you want variation — e.g. partition several
times and keep the best cut.
