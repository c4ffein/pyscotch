# Strategy Design Documentation

How PyScotch models Scotch strategies, and the design decisions behind it.
The API reference lives in `docs/API.md` and the docstrings of
`pyscotch/strategy.py`; this document explains *why* the API is shaped the
way it is.

## The contract

1. **`None` (or a fresh `Strategy()`, or `reset()`) means "Scotch's default
   strategy".** At the C level, a freshly `SCOTCH_stratInit`-ed strategy
   holds a NULL internal pointer; each compute routine that receives one
   builds its own adaptive default (tailored to the operation, part count,
   etc.). PyScotch keeps that meaning and spells it `None`.
2. **Every string is passed to Scotch verbatim — the same string means the
   same thing in PyScotch and in C Scotch.** PyScotch never rewrites,
   completes, or reinterprets a strategy string. This includes the empty
   string: see the traps below.
3. **Flag-based builds** (`request_mapping`, `request_ordering`,
   `StrategyFlags`) wrap `SCOTCH_stratGraphMapBuild` /
   `SCOTCH_stratGraphOrderBuild` — Scotch's own high-level templates. These
   are the recommended way to express "quality" / "speed" / "recursive"
   intent, because they are complete by construction.

## Known traps in the string grammar

These are upstream behaviours, reproduced verbatim per rule 2 (see
`QUESTIONS_FOR_SCOTCH_TEAM.md` for the questions raised with the Scotch
team):

- **`""` is a real, do-nothing strategy — not the default.** Mapping leaves
  every vertex unassigned (-1); dgraph mapping puts every vertex in a single
  part (which can look valid); ordering returns the identity permutation;
  overlap partitioning assigns nothing (PyScotch pre-fills the output with
  -1 so this is visible). Use `None` for the default.
- **Implicit sub-strategies are do-nothing dummies.** Bare method codes —
  `"r"`, `"m"` (mapping), `"n"`, `"c"` (ordering) — parse successfully but
  run with `stratdummy` internals: one part gets everything / the identity
  permutation comes back. Even parameterized strings are affected:
  `"r{job=t,map=t,poli=S,bal=0.05}"` omits `sep=` and silently degenerates,
  while `"r{sep=gf}"` works. PyScotch cannot detect incompleteness (the
  parse succeeds); verify outputs when hand-writing strings, or prefer the
  flag-based API.
- `"s"` (simple/natural ordering) is fine on its own — the natural order is
  exactly what it means.

## Deferred builds

`Strategy("...")` and `request_mapping`/`request_ordering` do not touch the
underlying `SCOTCH_Strat` at configuration time:

- Constructor strings cannot be parsed early because mapping and ordering
  use different grammars — only the consuming operation knows which one
  applies.
- Flag-based mapping builds need the part count, which is only known at
  `graph.partition(nparts, ...)` time.

The consuming operation therefore builds the recorded request into a
**private per-call strat** (~100 µs, negligible). Using a Strategy never
mutates it, so one Strategy can be shared across part counts and threads.
This also protects against an upstream subtlety: Scotch's implicit-default
build writes itself *into* the strategy object it is handed (the manual
documents this), which would otherwise leak a partnbr-pinned strategy into a
shared object.

Operations that cannot build a recorded request (dgraph and mesh operations
consume the raw strat) raise instead of silently running the default — use
`set_dgraph_mapping` / `set_dgraph_ordering` for those.

For tight loops, `built_for_mapping` / `built_for_ordering` /
`built_for_overlap` materialize the strategy once into a `BuiltStrategy`
handle valid inside a with-block, pinned to one operation family (and part
count) and cross-checked at every use.

## Presets

`Strategies.partition_quality()` / `partition_fast()` / `order_quality()` /
`order_fast()` are flag builds (`QUALITY` / `SPEED`) — real, distinct
strategies, not aliases of the default.

`set_recursive_bisection()` uses the genuine `RECURSIVE` flag. There are no
`set_multilevel()` / `set_nested_dissection()` counterparts: Scotch's default
*is* multilevel / nested-dissection-based and the `SCOTCH_strat*Build` API
has no flag to select them explicitly, so those helpers (which 7.0.0 shipped
broken, passing the bare `"m"` / `"n"` strings) could only ever alias the
default build — they were removed rather than kept as misleading no-ops.
Spell "default" as a plain `Strategy()`. (The CLI keeps `-s multilevel` /
`-s nested` as documented synonyms of `default`: there the word names the
algorithm the user gets, which really is multilevel / nested dissection.)

## References

- `pyscotch/strategy.py` — implementation and docstrings
- `QUESTIONS_FOR_SCOTCH_TEAM.md` — open upstream questions (empty string,
  bare method codes, `SCOTCH_stratFree`)
- `external/scotch/src/libscotch/library_graph_map.c` — implicit default
  build; `parser_yy.y` — the grammar's empty production
- `tests/pyscotch_base/test_strategy_requests.py`,
  `test_strategy_defaults.py` — behavioural pins for everything above
