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
calls, and nothing resets it implicitly.**

Reproducibility needs **two** things to hold, both inherited from how the
library was built and run:

1. **A fixed seed.** With `COMMON_RANDOM_FIXED_SEED` compiled in, every fresh
   process (and every `random_reset()`) restarts the stream from seed 1;
   without it, from `time(NULL)`. All standard builds have it — it is what
   CMake's default determinism level (`SCOTCH_DETERMINISTIC=FIXED_SEED`)
   compiles in, and `Make.inc` templates and `pyscotch scotch build` set it
   too. The build only chooses the *default*: to replace the seed at run
   time, call `pyscotch.random_seed(n)` then `random_reset()` — explicit,
   process-local, and reproducible. (Upstream also documents a
   `SCOTCH_RANDOM_FIXED_SEED` environment variable for this; in our testing
   it has no effect on the default stream.)
2. **Deterministic execution.** Without it, identical PRNG state still yields
   different results run to run — even across fresh processes — from two
   sources: thread scheduling (`SCOTCH_PTHREAD`), and PT-Scotch receiving
   point-to-point messages first-come-first-serve. Since Scotch 7.0 the fix is
   a **runtime** environment variable, no rebuild needed:

   ```bash
   SCOTCH_DETERMINISTIC=1 mpirun -n 4 python your_script.py
   ```

   This swaps only the nondeterministic kernels for deterministic ones (e.g.
   sequential matching, fixed-order message reception) — everything else stays
   threaded and fully multi-process, at some performance cost. Results are
   then reproducible for a fixed number of MPI ranks; with ≥ 2 threads the
   thread count doesn't matter (the 1-thread result differs — it is a separate
   code path). Alternatively `SCOTCH_PTHREAD_NUMBER=1` forces one thread,
   which handles the threading source only. Small graphs stay below the
   threading thresholds, which can make all of this easy to miss in tests.

With both in place, one variable remains: **the stream position**, which
advances with every randomized operation. It has to be taken into account
whenever a sequence of operations must replay identically — in unit tests, or
when re-running a series of operations to check that results are consistent:
call `pyscotch.random_reset()` (or pass `reset_random=True` to a high-level
operation) to restart the stream at the seed.

**All MPI processes draw the same random numbers by default.** A *rank* is
one of the N copies of your program that `mpirun -n N` launches; each has its
own private PRNG state, since processes share no memory. Because the seed
ignores the rank number, those N private streams are identical: as long as
every rank performs the same operations, they all draw exactly the same
sequence.

What is that *for*? The observable guarantee: identical computations agree.
If every rank of your application calls **sequential** PyScotch on the same
graph (a common pattern when the graph fits in memory), all ranks obtain the
same partition — provided the deterministic-execution conditions above hold —
and no result depends on which rank produced it. Upstream's stated rationale
(`common_integer.c`): the seed ignores the rank *"in order for
multi-sequential programs to have exactly the same behavior on any
process"*.

PT-Scotch itself does **not** rely on lockstep for agreement. In its
gather-and-compute-sequentially phases, every rank computes its *own*
candidate partition — the streams have usually drifted apart by then, so the
candidates genuinely differ — and a tiny election picks the winner: an
`MPI_Allreduce` with a "best partition" operator, then a broadcast from the
winning rank (`bdgraph_bipart_sq.c`). Divergence between ranks is harvested,
not feared.

Accordingly, if ranks draw *unevenly* — say your code partitions a rank-local
sequential graph on rank 0 only, between collective operations — their stream
positions diverge, and that is not a correctness hazard: it is the normal
state PT-Scotch's own algorithms operate in, and in our testing deliberately
desynchronized streams entering a collective `Dgraph` operation produced
valid, balanced partitions. Restore identical streams only when you *want*
the replicated-computation guarantee back: have **every rank** call
`pyscotch.random_reset()` before the next operation — the same explicit tool
as everywhere else on this page.

Two escape hatches exist, both user-invoked, mirroring the C API one-to-one:

- `pyscotch.random_proc(rank)` (then `random_reset()`) folds a process number
  into the seed when you *want* decorrelated ranks; `random_proc(0)` restores
  the default, bit-for-bit;
- `Context.random_clone()` gives a context its own private stream — seedable
  and resettable via `Context.random_seed()` / `Context.random_reset()`, and
  deliberately *not* touched by a global `random_reset()`.

Finally, the reason the stream advances at all: partitioning is a randomized
heuristic. Each call starts from different draws and lands in a different
local optimum — a different, equally valid partition whose quality varies a
little. Quality means the **edge cut**: the number of edges whose endpoints
fall in different parts, i.e. the communication your application will pay.
Leaving the stream running turns repetition into exploration:

```python
src = np.repeat(np.arange(nvert), np.diff(verttab))
cut = lambda part: int((part[src] != part[edgetab]).sum()) // 2
best = min((g.partition(4) for _ in range(10)), key=cut)
```

Every attempt respects the balance constraint; you are choosing among valid
partitions on cut alone. Expect no gain on regular graphs (a grid's optimal
cut is found every time) and spreads around a percent on irregular ones —
worth harvesting when the partition feeds a long-running computation. This
exploration is exactly what an implicit per-call reset would destroy: every
attempt would be the same attempt.

Note the parallelism layers here: the snippet is the *sequential* API — the
ten attempts run one after another, each internally thread-parallel
(`partition()` is where the parallelism lives). To parallelize the attempts
themselves, replicate the graph on every rank, decorrelate the streams
(`random_proc(rank)` then `random_reset()`), and reduce on the smallest cut —
k attempts for the wall-clock of one. On a distributed `Dgraph` the loop must
instead be written collectively: every rank calls `part()` together and the
cut needs a global reduction; lockstep streams then make all ranks agree on
the winner with no extra synchronization. Scotch can also select internally
in a single call: the strategy grammar's `|` operator runs two strategies and
keeps the better result.
