# upstream/ — PyScotch as Scotch's external QA

Everything PyScotch produces *for* Scotch rather than for its own users:
bug reports, proposed fixes, the experiments behind them, and the raw material
they were triaged from. The project's identity (see the "Claude on Scotch"
talk) is half Python binding, half independent test-bench for a 30-year-old
C/MPI library — this directory is the second half.

| Path | What | Status of its claims |
|---|---|---|
| `QUESTIONS_FOR_SCOTCH_TEAM.md` | Every upstream finding, with `file:line`, a mechanism and a repro that needs no PyScotch | **Verified** — each entry was reproduced against a built library |
| `proposals/` | Patches proposed upstream that PyScotch does *not* apply itself | Verified; see each entry |
| `experiments/` | Research tooling behind the findings (e.g. the strategy-parser differential fuzzer) | Tools, not claims |
| `scotch-static-analysis-history/` | Dated snapshots of large static code reads, kept as history | **Unverified leads** — see its README |

The patches PyScotch *does* apply live in `pyscotch/_scotch_patches/` (they
ship inside the package); a fix can be both a proposal and a shipped
behavioral patch — the shipped copy is the source of truth, this directory
only lists it.

## The loop

1. A lead appears — a flaky test, a differential mismatch, a fuzzer crash, a
   static-analysis finding below.
2. Reproduce it through PyScotch's oracles: `make test-differential` (byte
   identity with gpart/gord/gmap/dgpart/dgord), `make test-reproducibility`
   (N fresh runs must agree), the ported C tests, or a one-file repro.
3. If it reproduces: an entry in `QUESTIONS_FOR_SCOTCH_TEAM.md` with a
   C-only repro, and — when we can — a patch in `proposals/` (or, if it
   blocks us, a quickfix/behavioral patch in `pyscotch/_scotch_patches/`).
4. Report upstream (gitlab.inria.fr/scotch/scotch). Fixes have landed the
   same day, the next day, or within ten days.
5. When upstream ships the fix: move the entry to "Resolved upstream" and
   retire the patch.

To try a Scotch improvement end to end: build a patched Scotch with
`pyscotch scotch build <version> --pristine` plus your patch (or a behavioral
patch via `--auto-allow-behavioral-patches`), point `PYSCOTCH_LIB_DIR` at it,
and run the oracles above against it.
