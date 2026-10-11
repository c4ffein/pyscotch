# Spike: hand-written strategy-string parser + differential fuzzer

**Status:** Phase-1 proof-of-concept. Not wired into the build; lives here as a
spike to de-risk the "replace flex/bison with our own parser" idea before we
take it upstream. See `tasks.md` (root) for the two-phase plan and the
motivation.

## What this is

Scotch parses strategy strings (`"m{asc=f{move=200},low=r{sep=gf}}"`, the
`-s` argument to `gmap`/`gord`, the argument to `SCOTCH_stratGraphMap`, …) with
a flex/bison front-end (`parser_ll.l` + `parser_yy.y`). Its diagnostics go only
to `SCOTCH_errorPrint` (stderr) plus a 0/NULL return; a failed parse silently
restores the default; and building it needs flex ≥ 2.6.4 + bison.

`parser_rd.c` is a **front-end-only** hand-written recursive-descent
reimplementation. It produces the *same* `Strat` / `StratTest` trees off the
*same* method/parameter/condition tables, so everything downstream
(`parser.c` tree ops, `stratTestEval`, `stratSave`, `stratExit`) is untouched.
No flex, no bison, no reentrancy machinery.

**Phase-1 contract (strictly behaviour-preserving):** accept exactly the
strings bison accepts; build trees whose `stratSave` serialization is
byte-identical; emit the same hollow-parameter warnings. Sharper *message
text* is allowed — accept/reject verdicts and trees are the contract. (The
error-transport improvements and the semantic fixes for the traps below are
Phase 2, deliberately kept out so the equivalence claim stays falsifiable.)

## Files

| file | role |
|------|------|
| `parser_rd.c` | the recursive-descent parser (`stratParserParseRd`) |
| `differ.c` | differential harness: bison vs RD, `stratSave` as oracle; forks per input so a crash in either parser is contained and attributed |
| `dump.c` | dumps upstream's own generated default strategies (`SCOTCH_stratGraphMapBuild`/`OrderBuild` over the flag space) as fuzzer seeds |
| `gen.py` | corpus generator: hand-written corpus + seed mutations/recombinations, deterministic under `--seed` |
| `repro.c` | minimal single-string characterizer (parse → save → exit, breadcrumbs) |
| `build.sh` | builds `differ` and `dump` against the prepared source + stock `libscotch.so` |

## Running it

```sh
make build-gpart          # (repo root) prepares build/scotch-src + scotch-builds/bin/libscotch.so
cd upstream/experiments/parser-rd
./build.sh
./dump > seeds.txt
python3 gen.py --seeds seeds.txt --count 20000 --seed 42 > corpus.txt
./differ < corpus.txt          # exit 0 = no divergences; -v prints diagnostics
```

The harness checks each string against all four sequential grammars (graph
mapping, graph ordering, overlap partitioning, mesh ordering), compares
accept/reject verdicts, byte-compares `stratSave` on double-accepts,
re-parses the saved form and compares again (canonicalization stability), and
compares warning counts.

## Results (20 222 strings × 4 grammars ≈ 81 k parses, seed 42)

- **Zero divergences on agreement.** Every string both parsers accept produces
  a **byte-identical `stratSave`**, canonicalizes identically, and yields the
  same warning count. The Phase-1 equivalence holds across the whole corpus.
- **RD parser: 0 crashes. Bison: 246 crashes.** All 246 are the bison parser
  SIGSEGVing on malformed input; the RD parser rejects every one cleanly.
  Minimal repro `r{sep=m{}}` — a syntax error inside a strategy-valued
  parameter hits a NULL `paraptr` in the `PARAMVAL : error` action. Reported
  in `QUESTIONS_FOR_SCOTCH_TEAM.md` (crash-on-untrusted-input / DoS class).
- **139 verdict mismatches, all one upstream bug.** Every one is
  bison-accepts / RD-rejects, and every one is the empty-scalar-value trap
  (`f{move=}`, `r{map=}`, `b{width=|}`): bison stores a stray strategy pointer
  into a scalar slot, producing a tree that saves as garbage or (case slots)
  segfaults. RD rejects them. The single WARN mismatch is a consequence of one
  such verdict difference, not independent. Also reported upstream.

So on **valid** strategy strings the RD parser is already a drop-in match; the
only behavioural differences are it declining to reproduce two upstream bugs.

## Not done (Phase 2 and beyond)

- Parallel (`dgraph`) grammars — the harness covers the four sequential tables.
- Structured error transport (position + expected-token as *return data*, not
  stderr) — the whole point of the exercise; the RD parser already tracks the
  positions, they just need to reach the caller.
- Decisions on the two traps (reject empty scalar values? fix the crash?) —
  pending the Scotch team, since they change accept/reject semantics.
- Upstream integration path (keep `.y` as documentation + a CI differential
  test, or replace it). Discuss before building.
