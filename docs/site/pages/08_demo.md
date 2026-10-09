# The Ten-Minute Demo

A guided arc from an empty directory to PT-Scotch under `mpirun` — the demo
we'd give Scotch's own authors. Every Python script on this page runs in CI
like any other example; the `download` button on each block gives you the
file to run along.

## Act 0 — Clean Room

```bash
mkdir scotch-demo && cd scotch-demo          # drop the downloaded demo_*.py here
export PYSCOTCH_HOME=$PWD/pshome             # hermetic: managed builds land HERE
uv venv && source .venv/bin/activate
```

`PYSCOTCH_HOME` keeps the demo self-contained — nothing touches your real
`~/.local/share/pyscotch`, and Act 3's build is one `rm -rf` to undo.

## Act 1 — Install, Doctor, Partition

```bash
uv pip install "pyscotch[parallel]"          # wheels bundle libscotch, both int widths
pyscotch doctor
```

The doctor names the loaded backend (the wheel's bundled libraries), its
version, integer width, symbol suffix, and capabilities — and it stays useful
precisely when things are broken; diagnosing is its job.

{% example "demo_api.py" %}

Things to notice in the output: NumPy in, NumPy out; reproducibility is
*explicit* — the script sets `SCOTCH_DETERMINISTIC=1` and calls
`random_reset()` itself, because PyScotch never resets the PRNG behind your
back (fixed seed + deterministic execution + stream position, exactly the
[C semantics](06_parallel_pyscotch.html#reproducibility-across-ranks)); and
the running stream harvested as best-of-N exploration on an irregular graph —
the whole run, exploration spread included, replays identically.

The script saved `grid.grf`, so the CLI can take over:

```bash
pyscotch info grid.grf
pyscotch partition grid.grf -n 4 -o grid.map
pyscotch order grid.grf -o grid.ord
```

## Act 2 — Strategy Strings, Made Safe

{% example "demo_strategy.py" %}

In C, `"m"` parses and silently builds a do-nothing multilevel. PyScotch
refuses it at construction — *using Scotch's own parsers and
`SCOTCH_stratSave` as the detector*, never a reimplementation of the grammar —
and the [typed builder](05_using_pyscotch.html#composing-strategy-strings-the-typed-builder)
makes the hollow-slot trap unrepresentable.

## Act 3 — Build Upstream's Source Through the CLI

```bash
pyscotch scotch build --parallel --use       # pinned tarball from gitlab.inria.fr
PYSCOTCH_PARALLEL=1 pyscotch doctor          # Source line flips: user-built PT-Scotch
pyscotch scotch list
```

Checksum-pinned source, a toolchain preflight with distro-specific fixes, no
root — and the `use`d build now outranks the wheel's bundled libraries. Then
drive it (download the script, run it with `mpirun`; it also works *without*
a launcher — MPI singleton init makes it a valid 1-rank job, debugger-friendly):

```bash
PYSCOTCH_PARALLEL=1 mpirun -n 2 python demo_parallel.py
python demo_parallel.py                      # same script, 1 rank, no launcher
```

{% example "demo_parallel.py" collapsed %}

**Optional encore — the quickfix system.** Some upstream releases don't
compile under PyScotch's suffixed build (7.0.12 omits `SCOTCH_meshBuildElem`
from its symbol-rename table). PyScotch ships the fix and applies it
automatically:

```bash
pyscotch scotch patches
pyscotch scotch build 7.0.12 --sequential    # watch "Applied quickfix" fly by
pyscotch scotch list                         # the build is marked [quickfix]
```

## Act 4 — The Receipts

Claims this demo rests on, and where they're enforced:

- **Differential tier**: under deterministic settings, PyScotch's outputs are
  byte-identical to `gpart`/`gord`/`gmap` — and `dgpart`/`dgord` under mpirun
  (`make test-differential`).
- **Golden master**: the full sdist user journey — every command, every
  *expected failure message* — locked byte-for-byte in CI.
- **These very scripts**: each block on this page runs as a test on every
  change.

If anything goes sideways mid-demo, `pyscotch doctor` is the recovery path:
run it, read the fix line, do what it says. (That's also the pitch.) If
`mpirun` refuses for lack of slots on a laptop, add `--oversubscribe`.
