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

## Per-version reports

`scripts/gen_upstream_report.py` turns our verification data into one report per Scotch version (one HTML page, the
same content as a PDF, and a plain-text email draft that is never sent), with an index of every finding at the top: every finding with its status in that version, how it was
verified (ran it, or source read only, and why not run), the 7.0.x location, and two or more fix options. `make
upstream-report SCOTCH=7.0.17` builds it; `make docs-serve` serves it locally next to the docs.

- **Third-party leads are cited, not copied.** A finding keeps its original identifier (`COR-01`) and the
  author's name; its title, description and fix text are never reproduced, only re-stated in our own words.
  `ingest` drops the original titles on purpose.
- **One id per finding, across versions.** `upstream/reports/<version>/` holds only what depends on that release:
  `findings.json` (status, location, evidence, fix options in that version), the per-group patches and
  alternatives against that base, the combined `series/`, the group summaries and raw audits under `groups/`,
  and the build-and-test matrix `qa.json`. The reproducer kits do not depend on the release and live once in
  `upstream/repro/<group>/` (each finding points at `<group>/<id>`); a later version adds or updates kits, it
  does not copy them. A finding recorded by several groups is one entry with the other groups' views under
  `also`. Only the rendered report (`out/`) is gitignored. The docs site renders all of it as the Tracker
  (`docs/site/gen_analysis.py`, linked from the docs footer).
- **A report is a column, not a restart.** Each finding carries its history across versions, so the next
  report (including release candidates, `7.0.18rc1`) is "what changed since the last one".

- **The process behind 7.0.17** (agent brief and prompts, full test logs, the series as a git bundle, the
  transcripts of all 98 agents) is in a separate [handoff archive](https://raw.githubusercontent.com/c4ffein/static-files/d5bd26372a8e9e37bd0ebcfea5d00127a6b790d6/projects/pyscotch/pyscotch_reports/pyscotch-scotch-7.0.17-handoff-clean.tar.xz), next to the
  [review it started from](https://raw.githubusercontent.com/c4ffein/static-files/d5bd26372a8e9e37bd0ebcfea5d00127a6b790d6/projects/pyscotch/external_reports/scotch-bug-review-7-oct-2026-1c64e542-dc42-4f69-b178-bc8b576c5a58.pdf); [their README](https://github.com/c4ffein/static-files/blob/d5bd26372a8e9e37bd0ebcfea5d00127a6b790d6/projects/pyscotch/README.md) lists contents and sha256. A new round
  starts from the archive's `HANDOFF.md`.

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
