# Questions for the Scotch team

Notes collected while developing PyScotch, per the convention in CLAUDE.md:
places where tests could be more comprehensive, or where library behaviour
surprised us. References are to Scotch 7.0.11 sources unless noted.

**Re-audited against the 7.0.16 sources and a 7.0.16 build on 2026-10-02.**
Sections marked FIXED were resolved upstream in the stated release; every
other section was re-checked and is unchanged in 7.0.16 (the files cited
did not change, or the repro still reproduces).

## Strategy-string grammar: implicit sub-strategies are do-nothing dummies

The default value for every `STRATPARAMSTRAT` parameter in the public string
grammar is `&stratdummy` (e.g. `kgraph_map_st.c`, `kgraphmapstdefaultrb` /
`kgraphmapstdefaultml`). Consequently a user-supplied mapping strategy such as
`"r"`, `"m"`, or even `"r{job=t,map=t,poli=S,bal=0.05}"` parses successfully
but puts **every vertex into one part**, because the recursion runs with a
bipartitioning strategy that does nothing. Ordering behaves the same way:
`"n"` or `"c"` return the identity permutation. Only fully spelled-out strings
(e.g. `"r{sep=gf}"`) do real work.

- Is this intended? Accepting `"r"` and silently producing a degenerate result
  seems like a trap — an error, or defaulting to the strategy that
  `SCOTCH_stratGraphMapBuild(SCOTCH_STRATDEFAULT, ...)` would build for that
  method, would both be kinder.
- The C test suite does not appear to catch this because return codes are 0
  throughout (see "C Test Limitations" in our CLAUDE.md). A behavioural test
  asserting that `"r"` uses more than one part would document the intent
  either way.

## SCOTCH_stratGraphMap("") builds a do-nothing method

An empty string is accepted and installs an empty method: mapping leaves every
vertex at -1, ordering returns the identity. PyScotch used to treat `""` as
"use the default" (as several wrappers seem to) and shipped a partitioner that
returned all -1. Current PyScotch policy: strings — `""` included — are passed
to Scotch verbatim (same string, same meaning as C), and `None` / an untouched
strategy selects the default. Is `""` an *intended* part of the grammar (the
empty production also serves the `a|` selection forms), or an accident? Would
rejecting `""` (or making it mean `SCOTCH_STRATDEFAULT`) at the C level be
acceptable upstream? The ordering dispatchers deliberately run the identity
ordering for the empty strategy ("always maintain a consistent ordering",
`hgraph_order_st.c`), which suggests the empty strategy is at least
half-intended — a documented statement either way would settle what wrappers
should do.

The parallel API behaves the same way: `SCOTCH_stratDgraphMap("")` /
`SCOTCH_stratDgraphOrder("")` parse into a non-NULL empty strategy, so
`SCOTCH_dgraphMapCompute` / `OrderCompute` skip their build-default-when-NULL
path and run the do-nothing method. Observed on 7.0.12 (`mpirun -np 2`,
`bump.grf`): mapping puts all 9800 vertices in part 0 (no -1s, so it even
looks like a valid result), ordering returns the identity permutation.

## SCOTCH_graphPartOvl("") leaves the output array untouched

Worse than the mapping case above: with an empty (or any do-nothing) overlap
strategy, `SCOTCH_graphPartOvl` returns 0 but never writes `parttab` at all.
`library_graph_part_ovl.c` pre-assigns `grafdat.parttax` to the caller's
array, so `wgraphAlloc` skips its initialization branch, and since no method
runs nothing is ever stored — the caller gets back whatever memory happened to
be in the buffer (verified on 7.0.12: a sentinel-filled input array survives
the call byte-for-byte). With an uninitialized buffer this can look like a
plausible partition. Initializing `parttax` to -1 in `wgraphAlloc`
unconditionally (or documenting that `parttab` is only defined when a method
ran) would remove the trap. PyScotch now pre-fills the buffer with -1 before
the call.

## A failed strategy-string parse silently restores the default

Every string setter follows the pattern
`if ((*straptr = stratInit (tab, string)) == NULL) { errorPrint; return (1); }`
after having already freed the previous tree — so after a *failed*
`SCOTCH_stratGraphMap(&s, "bad{string")`, the strategy is back to the
untouched (NULL) state, and the next compute call silently runs the default
strategy. A caller that ignores the return code (the error is only visible
via `errorPrint` and the return value) gets default behaviour where they
asked for a custom strategy. Restoring the previous tree, or leaving the
strategy in a poisoned state that fails at compute time, would fail faster.
(PyScotch raises on the nonzero return, so this only bites C users.)

## SCOTCH_stratFree is public but undocumented — is it the intended "back to default"?

Since the compute routines build the implicit default *into* the caller's
strategy object (e.g. `library_graph_map.c`, "on return, the strategy object
will contain a fully specified strategy" per the manual), the only way to
return an object to "use the default" is to bring its inner pointer back to
NULL. `SCOTCH_stratFree` does exactly that (`library_parser.c`), is exported
and has a Fortran binding — but has no section in the user manual, and
nothing in the Scotch tree calls it (the CLI tools hand-roll
`SCOTCH_stratExit` + `SCOTCH_stratInit` instead, e.g. `gord.c`, `dgord.c`).
Is `stratFree` the sanctioned reset idiom wrappers should build on? A manual
section (and using it in the CLI tools) would make that discoverable.
Related: `SCOTCH_stratSave` dereferences the inner pointer without a NULL
check, so it segfaults on a freshly `stratInit`-ed strategy — a NULL check
printing e.g. `()` would make the "is it still default?" question answerable
from user code.

## Per-context SCOTCH_OPTIONNUMDETERMINISTIC does not make partitioning deterministic (env var does)

Setting the deterministic option on an explicit context does not produce
deterministic partitioning under threads, while the `SCOTCH_DETERMINISTIC=1`
environment variable does. Observed on 7.0.11/7.0.12 (64-bit, threaded build,
256-vertex `m16x16` graph, `SCOTCH_randomReset` before every call):

```c
SCOTCH_contextInit (&ctx);
SCOTCH_contextOptionSetNum (&ctx, SCOTCH_OPTIONNUMDETERMINISTIC, 1);  /* readback confirms 1 */
SCOTCH_contextBindGraph (&ctx, &graf, &bgraf);
SCOTCH_graphPart (&bgraf, 4, &strat, parttab);  /* 10 runs -> 2 distinct results */
```

whereas `SCOTCH_DETERMINISTIC=1` in the environment gives 10/10 identical
results with the same code path (implicit context) and threads enabled.

- Is an additional step required for explicit contexts (e.g.
  `SCOTCH_contextThreadImport*` before bind), or is this a bug?
- Related observation, in case it is intended: with `SCOTCH_DETERMINISTIC=1`,
  runs with 2, 4 and 8 threads all agree with each other but differ from the
  1-thread result. INSTALL.txt's "fully deterministic behavior with any number
  of threads" might deserve a footnote either way.
- PT-Scotch side works as documented: without the option, 3 identical
  `mpirun -n 2` runs on a 12x12x12 grid gave 3 different partitions
  (first-come-first-serve reception); with `SCOTCH_DETERMINISTIC=1`, 3/3
  identical. A regression test asserting that would pin the contract.

## CMake: unknown SCOTCH_DETERMINISTIC values silently mean NONE

`libscotch/CMakeLists.txt` handles the determinism level as
`if FULL / elseif FIXED_SEED / else -> none`, and the `STRINGS` cache property
is advisory only. So a typo (`-DSCOTCH_DETERMINISTIC=FIXEDSEED`,
`=fixed_seed`, ...) silently produces a time-seeded, non-deterministic build,
with only a `message(STATUS "Determinism: none")` in the configure output. A
`message(FATAL_ERROR ...)` on unrecognized values (or case-insensitive
matching) would fail fast instead. Same pattern may apply to other STRINGS
options (e.g. INTSIZE) — not audited.

## SCOTCH_RANDOM_FIXED_SEED environment variable appears to have no effect

INSTALL.txt (3.9) documents `SCOTCH_RANDOM_FIXED_SEED=0` as selecting "a new,
dynamically-changing pseudo-random seed at every run". Empirically (7.0.11,
build WITH `COMMON_RANDOM_FIXED_SEED`): two fresh single-threaded runs with
`SCOTCH_RANDOM_FIXED_SEED=0`, seconds apart, produce identical partitions.
`context.c` parses the variable into `CONTEXTOPTIONNUMRANDOMFIXEDSEED`, but no
other file reads that option — the global generator's seed is decided in
`intRandInit()` from the compile flag alone. Dead knob, or are we misreading
where it is meant to apply (context clones only)? `SCOTCH_randomSeed()` +
`SCOTCH_randomReset()` do work as the runtime replacement.

## PT-Scotch PRNG streams across ranks: divergence is by design — finding, plus a doc request

Two questions we started with, and the answer our own differential tests gave.

**The questions.** The default seed deliberately ignores the process rank
("multi-sequential programs have exactly the same behavior on any process",
`common_integer.c`). Read one way, that suggests replicated phases count on
identical draws on every rank for agreement without communication — so user
code that makes an *uneven* number of randomized sequential Scotch calls
across ranks (desynchronizing the streams) before a collective might get
invalid or inconsistent results. Read the other way, it is the opposite:
`bdgraphBipartMlUncoarsen` selects the best per-process candidate partition
via a custom `MPI_Allreduce` operator (`bdgraphBipartMlOpBest`, smallest rank
on a draw), and since nothing inside the library calls `intRandProc`, those
candidates can only differ because rank streams have *naturally diverged*
during the distributed phases (each rank draws in proportion to its local
work) — i.e. the fold-dup mechanism harvests desync rather than fearing it.

**The answer (7.0.13, empirical).** Building a byte-for-byte differential of
PyScotch's `Dgraph` against `dgpart`/`dgord` (`mpirun -np 2`,
`SCOTCH_DETERMINISTIC=1`) settled it. The library seed is rank-independent,
but the CLI tools do *not* leave it that way: each calls
`SCOTCH_randomProc(proclocnum)` at startup (`dgord.c:159`, `dgmap.c:181`),
making every rank's stream rank-dependent from the outset. So candidate
diversity is bootstrapped by explicit per-rank seeding, then compounded by
natural divergence. Evidence: a wrapper that only resets the seed (identical
on all ranks) is byte-identical to the tools on trivial graphs (small,
unweighted) but diverges — to a different yet *valid* result — the moment the
distributed multilevel path does real work (vertex-weighted `m16x16`, or
`bump` at 9800 vertices); adding `SCOTCH_randomProc(rank)` restores
byte-identity in every case. Our earlier desync probe (rank 0 burns 3 extra
sequential partitions, then a collective `SCOTCH_dgraphPart` on a 12x12x12
grid, 2 ranks, 3 runs) likewise produced valid, balanced partitions every
time. Conclusion: rank streams going out of sync is harmless for correctness
— the tools deliberately *create* the divergence — and a hypothetical future
rank-resynchronisation "fix" would silently *reduce* partition quality by
making all fold-dup candidates identical.

**What we would ask for.** (a) A one-line user-manual note that reproducing
`dgpart`/`dgord` from the library requires `SCOTCH_randomProc(rank)` per
process (the tools' first PRNG action) — it cost us a long hunt. (b) A
clarification of the `common_integer.c` comment: does "multi-sequential
programs" mean *user* applications replicating sequential Scotch calls across
ranks (a guarantee to users), or PT-Scotch's own multi-sequential phases
(which, per the above, elect rather than rely on identical streams)? The
distinction decides what user-facing guarantee the rank-independent seed is
meant to provide.

## SCOTCH_STRATSPEED ignored by stratGraphMapBuild; SCOTCH_STRATQUALITY by stratGraphOrderBuild

Verified structurally via SCOTCH_stratSave: `stratGraphMapBuild(SPEED, ...)`
produces the byte-identical string to DEFAULT (the mapping builder only
consults QUALITY/BALANCE/SAFETY/RECURSIVE), and `stratGraphOrderBuild(QUALITY,
...)` is byte-identical to its DEFAULT (the ordering builder honours SPEED but
not QUALITY). So "fast mapping" and "quality ordering" are the defaults under
other names. Intended (default = speed-leaning for mapping, quality-leaning
for ordering)? If so a doc note would help; if not, the flags are silently
ignored. PyScotch pins both equalities in tests
(`test_strategy_structure.py::test_upstream_pin_*`) so a change turns our
suite red.

## dorderPerm: debug-mode early return is not collective-safe (PETSc valgrind report, 7.0.12/7.0.13) — FIXED in 7.0.14, two follow-ups remain

**Status (7.0.16 audit):** issues (1) and (2) below were fixed in 7.0.14 —
`58c4248` "Bugfix: clean up column blocks in hdgraphOrderNd() [report
P. Jolivet]" adds the `dorderDispose (cblkptr)` on the leaf path
(`hdgraph_order_nd.c:327` in 7.0.16), and `274a952` "Bugfix: allow for
proper return in debug mode" makes the `SCOTCH_DEBUG_DORDER2` check fold
into `reduloctab[1]` and `break` instead of returning before the
`MPI_Allreduce`. Still open in 7.0.16: the leaf path's `hdgraphOrderSt`
return value is still ignored (`:325`), `dorderNew` at `:362` is still not
NULL-checked (issue 3), and `parmetis_dgraph_order.c` still ignores the
`SCOTCH_dgraphOrderCompute` / `OrderPerm` return values. The analysis is
kept below for the record.

Analysis of a PETSc `ex73` / `MatPartitioningApplyND` valgrind report:
`dorderPerm: invalid parameters (1)` followed by "conditional jump depends on
uninitialised value(s)" at `dorder_perm.c:130`, the value having been created
inside MPICH's `MPIR_Allreduce` called from `dorder_perm.c:126`. Line numbers
match 7.0.12/7.0.13 sources (`dorder_perm.c` is unchanged between the two).
We read this as a chain of three distinct issues:

1. **`hdgraph_order_nd.c:320-328`: the "could not separate more" leaf path
   is missing a `dorderDispose (cblkptr)`.** This is the root cause, on a
   perfectly *legal* path — no prior failure needed. When a multi-rank
   subgraph cannot be separated further, the leaf is ordered by the default
   leaf strategy `ole=q{...}` = `hdgraphOrderSq`, which gathers the subgraph
   onto proc 0 of the sub-communicator (`hdgraph_order_sq.c:90`) — the only
   rank that ever sets `cblkptr->typeval` (`hdgraphOrderSq2`, `:157/:160`).
   On every other rank the block stays at its `dorderNew` creation type
   `DORDERCBLKNONE` (`dorder.c:251`) and, unlike the three sibling
   `hdgraphOrderSt` call sites in the same file (`:382`, `:413`, `:430`),
   nothing ever disposes of the placeholder. Those `NONE` blocks are exactly
   what the `SCOTCH_DEBUG_DORDER2` check at `dorder_perm.c:104-110` calls
   "invalid parameters (1)". Non-debug builds work by accident: the `NONE`
   placeholders contribute 0 local vertices while the gather rank's `LEAF`
   block accounts for all of them, so the global-sum consistency check still
   passes — which is why this lay hidden.

2. **`dorder_perm.c:107-108`: the `SCOTCH_DEBUG_DORDER2` check `return (1)`s
   *before* the collective `MPI_Allreduce` at line 126.** The tree state is
   rank-local, so only the ranks holding the offending block bail out; the
   other ranks enter the allreduce, which MPICH then pairs with whatever
   collective the bailed-out ranks issue next (e.g. in
   `SCOTCH_dgraphOrderExit`) — mismatched signatures, so the reduction reads
   uninitialised bytes from its internal temp buffer. That is precisely the
   valgrind trace (allocation in `MPL_malloc` under
   `MPIR_Allreduce_intra_recursive_doubling`, use at `dorder_perm.c:130`),
   and it can equally deadlock or corrupt later collectives. Note the
   out-of-memory path just above (line 122-123) gets this right by folding
   the local failure into `reduloctab[1]` and letting *all* ranks agree via
   the allreduce; the debug check could do the same instead of returning.
   (In a non-debug build the same broken ordering is caught symmetrically and
   safely by the `reduglbtab[0] != grafptr->vertglbnbr` test — "invalid
   parameters (2)".)

3. **`hdgraph_order_nd.c:361`: `dorderNew()` result is not NULL-checked**
   before `cblkptr2->ordeglbval = ...` (its two siblings at lines 409 and 426
   are checked) — NULL dereference on out-of-memory.

A proposed fix (from the PETSc side) adds `dorderDispose (cblkptr)` after the
leaf ordering at `hdgraph_order_nd.c:325-327`. We reviewed it and believe it
is correct and complete for issue (1): it restores exactly the invariant the
three sibling call sites maintain; `dorderDispose` keeps locally-rooted
blocks, and the gather rank *is* the block's root rank (both are proc 0 of
the sub-communicator — `dorderNew`, `dorder.c:227-229`), so the typed `LEAF`
block survives where the leaf data lives while every other rank's `NONE`
placeholder is unlinked and freed; nothing dereferences the block afterwards
(children copy `fathnum` by value at creation, and a leaf has no children);
on a single-rank sub-communicator the dispose is a no-op. Their PETSc `ex73`
test passes under valgrind with the patch, consistent with all ranks now
reaching the allreduce together.

Remaining issues the patch deliberately leaves open — still worth fixing:

- the same line ignores `hdgraphOrderSt`'s return value (the separator path
  at `:380-384` checks `o != 0`; the leaf path doesn't), so a *failing* leaf
  ordering (e.g. gather out-of-memory) still returns success with an untyped
  block — recreating issue (1) on the failure path;
- `parmetis_dgraph_order.c:150-151` still ignores the return values of
  `SCOTCH_dgraphOrderCompute` / `SCOTCH_dgraphOrderPerm`, so any compute
  failure still reaches `dorderPerm` on a half-built ordering;
- issue (2): the debug check's non-collective early return remains, so any
  future `NONE` block turns into the valgrind mess / potential deadlock
  instead of a clean symmetric error;
- issue (3), the missing NULL check.

PyScotch is not affected: `Dgraph.order_compute()` raises on non-zero return,
so `order_perm()` can never run on a failed ordering.

## `SCOTCH_stratGraphMap` SIGSEGVs on a syntax error inside a strategy-valued parameter (7.0.13, still in 7.0.16)

A malformed sub-strategy in any `STRATPARAMSTRAT` slot crashes the parser with
a NULL-pointer dereference instead of returning a clean error. Minimal repros
(all `SIGSEGV`, verified on 7.0.13, both the flex/bison parser directly and
through `SCOTCH_stratGraphMap`):

```
r{sep=m{}}      m{low=m{}}      r{sep=(}      r{sep=(m}      b{bnd=(f}
```

while syntactically-invalid strings whose error is raised *outside* a nested
strategy value reject cleanly (return 1), e.g. `r{sep=qqq}`, `r{sep=m{bad=1}}`,
`r{bal=zzz}`, `r{sep=@}`, `r{poli=Q}`.

Root cause (`parser_yy.y`, line numbers as in 7.0.13):

- The `STRATPARAMSTRAT` production of `PARAMVAL` (the empty mid-rule action at
  lines 457-463) sets `penvptr->straptr = NULL` and `penvptr->paraptr = NULL`
  *before* parsing the nested `STRATSELECT`, restoring them only on success
  (lines 465-467).
- If the nested parse raises a syntax error that Bison recovers by reducing
  the `PARAMVAL : error` production (lines 481-487), that action dereferences
  `penvptr->paraptr->nameptr` and `penvptr->straptr->tablptr->...` — but
  `paraptr` (and, depending on how far the nested parse got, `straptr`) is
  still NULL. The dereference faults.
- The trigger is precisely a nested value that *begins* a sub-strategy and
  then errors while `paraptr` is NULL — e.g. a method with a malformed or
  empty brace list (`m{}`), or an unclosed group (`(`). A nested value that
  parses cleanly as the empty strategy (`sep=@`, `sep=!`) does not crash,
  because the error is raised later, after the pointers are restored.

Because strategy strings are frequently user- or config-supplied, this is a
crash-on-untrusted-input (DoS) class, not merely a diagnostics issue. A
guard printing e.g. `(unknown)` when `paraptr`/`straptr` are NULL in the
error action — or folding the failure into the normal error return the way
the non-strategy value paths do — would turn all of these into clean
rejections. Found via a differential fuzzer (bison parser vs. a hand-written
recursive-descent reimplementation, `stratSave` as the equivalence oracle):
over 20 000 generated strings the RD parser rejected every one of these
cleanly, so a reference for the intended accept/reject verdicts exists if
useful.

## Confirmed via fuzzing: empty scalar parameter value (`f{move=}`) builds a corrupt tree (7.0.13, still accepted in 7.0.16)

The same differential fuzzer confirmed and sharpened the empty-value trap.
`SCOTCH_stratGraphMap` accepts `f{move=}`, `f{bal=}`, `r{map=}`, `b{width=|}`
and similar — a parameter name and `=` with no value — for *scalar*
parameters (int, double, case), not only for strategy-valued ones. The empty
`PARAMVAL` production (`parser_yy.y:457-480`, the `STRATSELECT` alternative)
parses an empty sub-strategy and stores its `Strat *` pointer into the
parameter's slot regardless of the slot's declared type. For an int/double
slot the pointer is reinterpreted as the numeric value (so `SCOTCH_stratSave`
prints a garbage, ASLR-dependent number — e.g. `f{move=-1756790160,...}`);
for a case slot `SCOTCH_stratSave` indexes the selector string by that
pointer and **SIGSEGVs**. This is the scalar-slot analogue of the hollow
strategy-slot trap already documented above, and equally argues for rejecting
an empty value (or at least type-checking the slot before storing a strategy
pointer). PyScotch already rejects all of these at construction via its
both-grammar parse probe.

## SCOTCH_graphStat: `edlosum` counts arcs with edge loads, edges without (7.0.13, unchanged in 7.0.16)

`library_graph.c`, `SCOTCH_graphStat`: when the graph has an edge load array,
`edlosum` is accumulated over every arc (`for all edges` loop over
`verttax[vertnum]..vendtax[vertnum]`), so an undirected edge of load `w`
contributes `2w`. When the graph has **no** load array, the same output is
set to `edgenbr / 2` -- the number of undirected *edges*, i.e. `1` per edge
rather than `2`. The two branches therefore disagree by a factor of two for
the one case where they should coincide: a graph whose every edge has load
1 reports `edlosum = edgenbr` if built with an explicit all-ones `edlotab`,
and `edlosum = edgenbr / 2` if built without one. (`edlomin`/`edlomax`/
`edloavg` agree between the branches; only the sum differs.) `graph.h`
documents the field as "Sum of edge (in fact arc) loads", and
`SCOTCH_graphBuild` sets `edlosum = edgenbr` for unloaded graphs, so the
arc-based count looks like the intended one and the `/ 2` in `graphStat` the
slip.

Found by a Hypothesis property test on PyScotch's `Graph.from_edges`, which
omits the load array when every weight is 1; the test now pins the current
behaviour and will fail (so we notice) if the branch is changed.

## SCOTCH_graphOrderCheck never looks at `permtab` (7.0.13, unchanged in 7.0.16)

`order_check.c`, `orderCheck`: the routine validates `peritab` -- every entry
in `[baseval, baseval + vnodnbr)`, no duplicate, no missing index -- and then
the column-block tree (`orderCheck2`). `ordeptr->permtab` is never read. So an
ordering whose `permtab` is **not** the inverse of its `peritab` (two entries
swapped, say) passes `SCOTCH_graphOrderCheck` with return value 0, even though
`SCOTCH_graphOrderCompute` always produces the two as mutual inverses and
every consumer (`gotst`, the matrix-ordering users) assumes they are.

Since the API takes both arrays (`SCOTCH_graphOrderInit(..., permtab,
peritab, ...)`), the check seems like the natural place to also assert
`permtab[peritab[i]] == i` -- it is one extra pass over an array that is
already allocated there (the local `permtab` scratch array in `orderCheck` *is*
the inverse of `peritab`; comparing it against `ordeptr->permtab` when the
latter is non-NULL would do). Is leaving `permtab` unchecked intentional
(e.g. because `permtab` may legitimately be NULL / lazily filled), or an
oversight?

Found while testing PyScotch's `Graph.order_check` with deliberately
inconsistent inputs; `tests/pyscotch_base/test_array_conversion.py::
TestStridedViewsOnPublicPaths::test_order_check_only_inspects_peritab` pins
the current behaviour so we notice if it changes.

## SCOTCH_contextOptionSetNum switches on the option *value* instead of the option *index* (7.0.11, still in 7.0.16)

**Status (7.0.16 audit):** unchanged — `library_context.c:306` still reads `switch (optival)`.

*Added: 2026-07-12, found while writing behavioral tests for context options*

In `library_context.c` (v7.0.11), `SCOTCH_contextOptionSetNum()` contains:

```c
switch (optival) {                                /* <-- should be optinum? */
  case CONTEXTOPTIONNUMRANDOMFIXEDSEED :
    if (optitmp != 0)
      optitmp = 1;                                /* Only two values available */
    break;
  case CONTEXTOPTIONNUMDETERMINISTIC :
    if (optitmp != 0) {
      optitmp = 1;
      o = contextValuesSetInt ((Context *) libcontptr, CONTEXTOPTIONNUMRANDOMFIXEDSEED, 1);
    }
    break;
  default :
    errorPrint (STRINGIFY (SCOTCH_contextOptionSetNum) ": invalid option name");
    return (1);
}
```

The `switch` is on `optival` (the value being set) rather than on `optinum`
(the option index). Since `CONTEXTOPTIONNUMDETERMINISTIC == 0` and
`CONTEXTOPTIONNUMRANDOMFIXEDSEED == 1`, the dispatch accidentally "works" for
values 0 and 1, but the observable consequences are:

1. **The documented cascade never happens.** Setting
   `SCOTCH_OPTIONNUMDETERMINISTIC` to 1 is supposed to also force
   `SCOTCH_OPTIONNUMRANDOMFIXEDSEED` to 1 ("If deterministic behavior wanted,
   use fixed random seed"), but the value 1 lands in the
   `CONTEXTOPTIONNUMRANDOMFIXEDSEED` case, which only clamps. Reproduction:

   ```python
   ctx = Context()
   ctx.option_set(1, 0)   # RANDOMFIXEDSEED off
   ctx.option_set(0, 1)   # DETERMINISTIC on
   ctx.option_get(1)      # -> 0, expected 1 per the code's intent
   ```

2. **Values >= 2 are rejected instead of clamped.** The `if (optitmp != 0)
   optitmp = 1;` clamping code is unreachable for any value other than 0/1:
   e.g. `SCOTCH_contextOptionSetNum(ctx, SCOTCH_OPTIONNUMDETERMINISTIC, 2)`
   falls into `default:` and fails with "invalid option name" even though the
   option name is valid.

3. **Invalid option indices are only caught late.** E.g. option index 99 with
   value 1 is dispatched as if it were a fixed-seed update, and only fails in
   `contextValuesSetInt()`'s bounds check.

Our tests only assert the 0/1 round-trip behavior, which is identical whether
or not the `switch` is fixed; we did not encode the cascade or the clamping
in tests since both look unintended in their current form.

### Question

Should this be `switch (optinum)`? If so, is the cascading of
DETERMINISTIC=1 into RANDOMFIXEDSEED=1 the intended long-term semantics
(i.e., should PyScotch expose/emulate it)?

## Public functions declared in scotch.h but documented in neither user manual (7.0.11, still in 7.0.16)

**Status (7.0.16 audit):** unchanged — the 7.0.14–7.0.16 manual edits only add notes on the diffusion methods.

*Added: 2026-07-13, found while generating deep links from the PyScotch API
reference into the user manuals (function → page map extracted from the PDFs'
own bookmarks).*

Of the 149 public functions PyScotch binds, 8 appear in `scotch.h` /
`ptscotch.h` (v7.0.11) but in neither `scotch_user7.0.pdf` nor
`ptscotch_user7.0.pdf`:

- `SCOTCH_archBuild` (the manual documents `SCOTCH_archBuild0`/`archBuild2`,
  but not the plain `archBuild` also exported)
- `SCOTCH_archVar`
- `SCOTCH_graphGeomLoadMmkt` / `SCOTCH_graphGeomSaveMmkt` (Matrix Market
  geometry I/O; the other Geom formats are documented)
- `SCOTCH_graphOrderList`
- `SCOTCH_graphPartOvlView`
- `SCOTCH_randomSave` / `SCOTCH_randomLoad`

Is the omission intentional (semi-private API)? If so, a note in the headers
would help binding authors; if not, this list may help complete the manuals.

## Rename-table sweep: SCOTCH_contextAlloc is still missing from module.h (7.0.11, still in 7.0.16)

**Status (7.0.16 audit):** `SCOTCH_memFree` and `SCOTCH_meshBuildElem` were added to the table in 7.0.13 (see "Resolved upstream" below); `SCOTCH_contextAlloc` and the three `SCOTCH_error*` names are still absent from `module.h` in 7.0.16.

*Added: 2026-07-13, from a mechanical sweep of library.h vs module.h*

Cross-checking every public function in `library.h` against `module.h`'s
`SCOTCH_NAME_PUBLIC` rename table (v7.0.11 and v7.0.12) finds 5 absentees:
`SCOTCH_memFree` (reported above), `SCOTCH_meshBuildElem` (7.0.12, reported
above), **`SCOTCH_contextAlloc`** (exports unsuffixed while e.g.
`SCOTCH_graphAlloc_64` is correctly suffixed — verified with `nm`), and
`SCOTCH_errorPrint`/`SCOTCH_errorPrintW`/`SCOTCH_errorProg` (possibly
intentional, since the error library is shared between suffixed variants —
if so, a comment in module.h would make that explicit).

The sweep is a 15-line script; happy to contribute it as a CI check upstream
so this bug class cannot recur.

## libscotch.so under-declares its shared-library dependencies (no NEEDED for libz/libm/libpthread) (7.0.11, still in 7.0.16)

**Status (7.0.16 audit):** unchanged — a 7.0.16 `libscotch.so` built from the stock `Makefile.inc` still records `NEEDED = libc.so.6` only (the CMake side moved to imported `ZLIB::ZLIB` targets, which does not affect the Makefile build).

*Added: 2026-07-14, found while building self-contained binary wheels.*

`libscotch.so` calls into zlib (`gzread`, `gzclose`, …), libm, and libpthread,
but its dynamic section records `NEEDED = libc.so.6` only — the other
dependencies are undeclared:

```
$ nm -D scotch-builds/lib64/libscotch.so | grep -E ' U (gz|pthread_create|sqrt)'
                 U gzclose
                 U gzread
                 U pthread_create@...
$ readelf -d scotch-builds/lib64/libscotch.so | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so.6]     # libz/libm/libpthread absent
```

Root cause is in `src/Makefile.inc`: the shared object is created with
`AR = gcc`, `ARFLAGS = -shared -o` (i.e. `gcc -shared -o libscotch.so *.o`),
while `LDFLAGS = -lz -lm -lrt -pthread ...` is applied only when linking the
command-line executables. So the libraries never make it into the `.so`'s own
`NEEDED` list.

This is invisible in normal use — Scotch's executables supply the libraries at
their final link, and most distro packages re-link the shared object with
proper `NEEDED` — so it has clearly never caused a problem in practice. It only
surfaces when the *bare, as-built* `.so` is loaded standalone (e.g. `dlopen`'d
by a language binding) under eager binding: the manylinux toolchain links with
`-z now`, so the loader resolves every symbol up front and the import fails with

```
libscotch.so: undefined symbol: gzclose
```

Under the more common lazy binding it "works" until the first compressed-file
operation, which makes it a latent trap rather than an immediate error.

### Suggested fix (upstream)

Link the shared object with its libraries, or — cleaner — build it with
`-Wl,--no-undefined`, which makes the linker **reject** an under-declared shared
object at build time instead of silently shipping one. Either way the `.so`
becomes self-describing and every downstream that loads it directly benefits.

### Question

Is the shared library intentionally built to defer its library resolution to
the executable link, or would recording the real `NEEDED` entries (and/or adding
`-Wl,--no-undefined` as a guardrail) be a welcome change? We're happy to send a
small Makefile.inc patch if useful.

### What PyScotch does meanwhile

Two independent, self-sufficient layers (see
`scripts/build_wheel_libs.sh` step 3b and `pyscotch/libscotch.py`
`_preload_dependencies`): we stamp the honest `NEEDED` entries onto the bundled
wheel library with `patchelf`, and we also preload the dependency by runtime
soname (`libz.so.1`) before Scotch loads — the latter also covers an
under-linked *system* Scotch, which we cannot re-link.

## Suggestions (not defects)

### Best-of-N attempts: no numeric repeat construct in the strategy grammar?

The selection operator `|` is implemented in every strategy dispatcher
(sequential and parallel), and since the PRNG stream advances between the two
branches, chaining the *same* strategy — `"<s>|<s>|<s>"` — is a declarative
"try 3 times, keep the best". But N can only be expressed by syntactic
repetition of the full strategy text. Was a numeric construct (a `try(n, <s>)`
node, or a method parameter à la METIS `NCUTS`) ever considered? It would
compose better with generated strategies and avoid very long strings for
large N — and make the technique discoverable, since today nothing in the
grammar hints that `s|s` is meaningful with identical branches.

## Resolved upstream

Kept for the record; each was fixed in the stated release.

- **`SCOTCH_graphColor` produced invalid colorings on sparse graphs** (found
  2025-12-05 by `tests/hypothesis/test_graph_properties.py`) — fixed in 7.0.11,
  commit `e0a90c7`. Full story, original report, reproduction and source
  analysis: [COLORING_BUG_RESOLUTION.md](COLORING_BUG_RESOLUTION.md).
- **`SCOTCH_memFree` exported unsuffixed under `SCOTCH_RENAME_ALL`** (7.0.11,
  7.0.12): the suffixed `scotch.h` declared `SCOTCH_memFree_64` while the
  library exported plain `SCOTCH_memFree`, because the name was missing from
  `module.h`'s `SCOTCH_NAME_PUBLIC` rename table — a link failure for any C
  program built against the suffixed header. Fixed in 7.0.13. PyScotch still
  special-cases the unsuffixed symbol so older builds keep working.
- **7.0.12 did not build with `SCOTCH_RENAME_ALL`**: the new
  `SCOTCH_meshBuildElem` (commit `2285ed4`) had no rename-table entry, so
  `library_mesh_f.c:233` hit an implicit declaration error. Same root cause as
  `memFree`; fixed in 7.0.13. PyScotch's managed builder still applies
  `pyscotch/_patches/scotch-7.0.12-rename-all-fix.patch` to 7.0.12 automatically.
- **`dorderPerm` debug-mode early return / untyped leaf column blocks** —
  fixed in 7.0.14 (see that section above; two follow-ups remain open).
