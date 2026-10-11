# Common infrastructure — Scotch v7.0.11

## Scope

Shared infrastructure of libscotch, at `/home/dev/workspace/pyscotch/external/scotch/src/libscotch/`:
`common*.c` / `common*.h` (memory allocation and tracing, thread pool, pseudo-random generator,
file (de)compression, integer sorting, string substitution), `parser.c` + `parser_yy.y` +
`parser_ll.l` (strategy-string parser), and the naming machinery (`module.h` rename table,
`dummysizes.c` generation of `scotch.h` from `library.h`). Verified against the built
`scotch-builds/lib64/libscotch.so` (suffix `_64`) with `nm`. Submodule checked clean at tag
v7.0.11.

## Architecture

### Memory model (`common_memory.c`)

- `memAlloc/memRealloc/memFree` are thin macros over libc unless `COMMON_MEMORY_TRACE` or
  `COMMON_MEMORY_CHECK` is set, in which case `mem*Record` wrappers prepend a size header
  (`COMMON_MEMORY_SKEW`) and keep global counters `memorysiz`/`memorymax` (mutex-guarded only
  under `COMMON_PTHREAD_MEMORY`; the mutex itself is lazily initialized with an admitted race,
  common_memory.c:299 "Unsafe code with respect to race conditions").
- `memAllocGroup` (common_memory.c:488) packs N arrays into one malloc block: varargs of
  `&ptr, size` pairs, each offset padded to `sizeof(double)`. Two passes: sum sizes, then assign
  pointers. Consequence for bindings: **sub-array pointers returned via the group are not
  individually freeable** — only the first pointer (the block base) may be passed to `memFree`.
  There is no overflow check on the `memoff` accumulation, but sizes are `size_t` and overflow
  would require call-site products already overflowed (call-site concern, out of scope here).
- `memCheck*` (debug only) uses a fixed table of 10,000 blocks and 16 KiB sentinels around each
  allocation.

### Thread pool (`common_thread.c`, `common_context.c`)

- One `ThreadContext` per execution context; `threadContextInit` spawns `thrdnbr - 1` slave
  threads that park in `threadWait` on a condvar. `threadLaunch` broadcasts a function pointer +
  parameter; a custom condvar barrier (`threadContextBarrier`, generation-counted via `bainnum`)
  synchronizes rounds. Shutdown (`threadContextExit2`) sets status DWN and then **spin-locks**,
  repeatedly taking the mutex until all slaves acknowledge (common_thread.c:187-191).
- `contextThreadLaunchSplit` halves a context into two sub-contexts; sub-context 1 gets a fresh
  PRNG seeded from the parent's stream (`intRandSpawn`/`intRandSeed`), which is how nested
  parallelism keeps deterministic, distinct streams.
- Thread count resolution: compile-time `SCOTCH_PTHREAD_NUMBER`, overridable at run time by the
  `SCOTCH_PTHREAD_NUMBER` environment variable, `-1` = number of cores (common_context.c:216-227).

### PRNG (`common_integer.c`)

- Algorithm: xorshift128+ (`intRandVal3`, common_integer.c:421) over a 2×64-bit state in an
  `IntRandContext { flagval, procval, seedval, statdat }`. One **global** context `intranddat`
  (common_integer.c:196); `contextInit` points new contexts at it and calls `intRandInit`, which
  seeds from `time(NULL)` unless `COMMON_RANDOM_FIXED_SEED`/`COMMON_DEBUG` force seed 1.
- Determinism guarantees: same seed + same procval ⇒ same stream; `intRandReset` re-derives the
  state from `(seedval|1) * (procval+1)`, so `SCOTCH_randomReset` restores reproducibility only
  if the seed is fixed (fixed-seed build, `SCOTCH_randomSeed`, or context option). `intRandVal`
  is deliberately **not** thread-safe (comment at common_integer.c:406-415); determinism is the
  caller's job.
- `intRandVal(ctx, randmax)` reduces by plain `%` (common_integer.c:458) — see Findings.

### Strategy parser (`parser.c`, `parser_yy.y`, `parser_ll.l`)

- Flow: `stratInit(strattab, string)` → `stratParserParse` (parser_yy.y:797) → reentrant flex
  scanner over the string buffer + pure Bison parser (`%define api.pure full`), environment in a
  stack-local `ParserEnv`, so **parsing itself is reentrant/thread-safe** in 7.0. Method and
  parameter names are resolved against the per-library `StratTab`; the lexer switches start
  conditions (`PARSERLLBEGIN`) between strategy/parameter/test sub-grammars. Result is a `Strat`
  tree (`STRATNODECONCAT/COND/SELECT/METHOD/EMPTY`) freed by the recursive `stratExit`.
- Lexer copies method/param/string tokens into fixed 256-byte `%union` fields with `strncpy` +
  forced NUL (parser_ll.l:113-146) — silent truncation past 255 chars, no overflow.

### Rename/suffix machinery (`module.h`, `dummysizes.c`)

- Three name classes (module.h:244-307): `SCOTCH_NAME_INTERN(f)` = `_SCOTCH ## f ## suffix` for
  ~791 internal symbols listed one-by-one in module.h; `SCOTCH_NAME_PUBLIC(f)` = `f ## suffix`
  for the `SCOTCH_*` API (only when `SCOTCH_RENAME_ALL`/suffix builds); `SCOTCH_NAME_GLOBAL`
  (module.h:304) maps `errorPrint/errorPrintW/errorProg` to **unsuffixed** `SCOTCH_errorPrint*`
  in every build — libscotch.so carries them as *undefined* symbols satisfied at link time by
  `libscotcherr.so`/`libscotcherrexit.so` or by a user-provided definition (verified with `nm`:
  `U SCOTCH_errorPrint` in libscotch.so, `T SCOTCH_errorPrint` in libscotcherr.so). This is the
  interposition mechanism PyScotch relies on.
- `dummysizes.c` is a build-time generator: it is compiled with the real internal headers,
  measures `sizeof` of internal structs (Arch, Graph, Context, ...), and rewrites the
  `library.h` template's `DUMMYSIZE*` placeholders into padded `double` arrays to produce
  `scotch.h` (sizes in doubles for alignment, hence the `SCOTCH_*Sizeof()` guidance).
- Cross-check performed: every extern function compiled into libscotch.so from my territory is
  either in the INTERN table or intentionally GLOBAL; `nm -D` on the built lib shows **no**
  unprefixed leaked symbols from common*/parser* (the known `SCOTCH_memFree`/`SCOTCH_contextAlloc`
  suffix omissions are calibration items, not re-reported).

## Code-quality observations

- `threadContextExit2` busy-waits with mutex polling instead of a condvar for slave termination
  (common_thread.c:187-191); harmless but burns a core during shutdown.
- `stringSubst` (common_string.c) does unbounded in-place substitution; callers like
  `library_graph_map.c:659` use `char bufftab[8192]; /* Should be enough */`. Safe today because
  all templates are internal constants, but the invariant is unchecked and recursion is one level
  per pattern occurrence.
- Debug-only `memReallocRecord` delists the old block *before* calling `realloc`
  (common_memory.c:350); on realloc failure the still-live old block is no longer tracked, so a
  later `memFree` of it triggers a spurious "block not found" warning.
- `intLoad` (common_integer.c:108-115) accumulates digits with no overflow detection; absurdly
  large integers in input files silently wrap (robustness, not memory safety — it never reads
  past the terminator).
- `stratSave` case `STRATNODESELECT` falls through into `STRATNODEEMPTY` (parser.c:215-223);
  the fall-through only hits `break`, so behavior is correct, but it is an unannotated
  fall-through.

## Findings

1. **Strategy parser leaks partially built trees on syntax errors** — parser_yy.y (no
   `%destructor` anywhere in the file; checked with grep).
   Manual out-of-memory paths do clean up (e.g. parser_yy.y:158-161 `stratExit ($1); stratExit ($3); YYABORT;`),
   but on a plain *syntax* error Bison pops and discards the value stack, and without
   `%destructor` declarations every `Strat *` / `StratTest *` already reduced onto the stack is
   leaked. `stratParserParse` only frees `penvdat.straptr` (parser_yy.y:824-827), which is set
   solely by the final root reduction, so it is NULL on mid-parse failure. Mechanism: each call
   to `SCOTCH_stratGraphMap`-style routines with a malformed strategy string leaks the prefix of
   the tree parsed so far. Bounded per call, but unbounded for a long-lived process that
   repeatedly retries user-supplied strategies. Confidence: high (mechanism is standard Bison
   behavior; leak size depends on where the error occurs).

2. **`SCOTCH_randomVal(0)` crashes with SIGFPE; negative `randmax` yields a huge modulus** —
   common_integer.c:458 / library_random.c:141-146.
   ```
   return (((UINT) intRandVal3 (&contptr->statdat)) % randmax);
   ```
   `SCOTCH_randomVal` passes the user's `SCOTCH_Num` straight through as `(UINT) randmax`
   (library_random.c:145). `randmax == 0` is an integer division by zero (process-killing
   SIGFPE); `randmax < 0` becomes a near-2^64 modulus rather than an error. No validation on
   either the public or internal path (only a `COMMON_DEBUG` check for the *initialized* flag,
   not the argument). Confidence: high (arithmetic is unconditional).

3. **Uninitialized global PRNG is an all-zero xorshift fixed point: `SCOTCH_randomVal` returns 0
   forever if called before any init** — common_integer.c:196 + common_integer.c:421-436 +
   library_random.c:145.
   `intranddat = { 0, 0 }` leaves `statdat.randtab` zero (static storage). xorshift128+ maps the
   all-zero state to itself (`x=0, y=0` ⇒ output 0, state stays 0), so every draw is 0.
   `SCOTCH_randomVal` calls `intRandVal` directly without `intRandInit` (unlike
   `SCOTCH_randomReset`, library_random.c:116, and `contextInit`, common_context.c:81, which do
   init), and the `flagval == 0` guard exists only under `COMMON_DEBUG`
   (common_integer.c:451-456). Graph routines are unaffected (they init via `CONTEXTINIT`), but a
   user calling `SCOTCH_randomVal` first gets a degenerate constant stream with no warning.
   Related: `intRandLoad` (common_integer.c:335-361) sets `flagval = 1` and accepts an all-zero
   `randtab` from the file without validation, reaching the same stuck state. Confidence: high on
   the mechanism (code inspection; zero is a documented xorshift128+ forbidden state — the seeder
   itself guards against it at common_integer.c:232 "Never have a zero state", the loader and the
   BSS default do not).

4. **PRNG modulo reduction is biased** — common_integer.c:458. `x % randmax` over a 64-bit
   xorshift128+ output has bias ≈ `randmax / 2^64` per draw (32-bit builds: `randmax / 2^32`,
   noticeable for large `randmax`). For Scotch's use (index selection in heuristics) this is
   cosmetically irrelevant, but it means `SCOTCH_randomVal` is not uniform in the strict sense.
   Confidence: high on the math, low on practical impact — arguably by design for speed.

5. **`contextExit` dereferences NULL `valuptr` if `SCOTCH_contextInit` failed partway** —
   common_context.c:99-103.
   ```
   if (contptr->valuptr != &valudat) {             /* If not global values array           */
     if (contptr->valuptr->dataptr != contptr->valuptr->dainptr)
   ```
   `contextInit` leaves `valuptr = NULL`; it only becomes non-NULL via `contextOptionsInit`
   (allocation may fail, returning 1 with `valuptr` still NULL — common_values.c:80-85) or
   `contextCommit`. If `SCOTCH_contextInit` returns 1 from the "cannot create option array"
   branch (library_context.c:113-116) and the user then calls `SCOTCH_contextExit` (a natural
   cleanup response), `NULL != &valudat` passes and line 100 dereferences NULL. Only reachable
   on allocation failure, so low likelihood; confidence high on the code path itself.

6. **`intSearchDicho` is declared but defined nowhere** — common.h:455
   `INT intSearchDicho (const INT * const, const INT, const INT, const INT);`
   No definition in any `.c` file (repo-wide grep) and no `module.h` rename entry. Currently a
   dead declaration (no link error since nothing calls it); if it were ever implemented, the
   missing `SCOTCH_NAME_INTERN` entry would leak an unprefixed `intSearchDicho` symbol.
   Confidence: high; severity: trivial.

No other new findings in the reviewed files. Calibration items (module.h rename-table omissions
for `SCOTCH_memFree`/`SCOTCH_contextAlloc`, unsuffixed `SCOTCH_error*`, `contextOptionSetNum`
switch bug) were confirmed present but are not re-reported.

## Test coverage (src/check/)

- `test_common_random.c` (213 lines): good coverage of *reproducibility* — draws, reset, redraw,
  compare; save/load round-trip when `COMMON_RANDOM_FIXED_SEED` allows. **Gaps**: never calls the
  public `SCOTCH_randomVal` (so findings 2 and 3 are untested), no edge cases (`randmax` 0/1/
  negative), no distribution sanity check, no test of loading a corrupt/zero state file.
- `test_common_thread.c` (215 lines): exercises launch/barrier/reduce/scan. Gap: no context
  split (`contextThreadLaunchSplit`) test, no thread-count-1 vs N equivalence check.
- `test_common_file_compress.c` (144 lines): compress/decompress round-trip per built algorithm.
  Gap: no truncated/corrupt-stream decompression test (error paths in `fileDecompress*`
  unexercised).
- `test_strat_seq.c` / `test_strat_par.c`: only call `SCOTCH_stratGraphMapBuild`-family with
  the *built-in* flag combinations — they test template generation, **not** the parser proper.
  Gaps: no malformed-strategy tests (finding 1 unexercised), no parse → `stratSave` → reparse
  round-trip, no parameter-out-of-range tests.
- Nothing tests `memAllocGroup`, `intSort*` (sortedness/stability), `stringSubst`, or
  `fileNameDistExpand`.

## PyScotch relevance

- **`SCOTCH_randomReset` semantics**: it re-derives state from the stored seed (default:
  `time(NULL)` captured at first init). It gives run-internal reproducibility (same process,
  same sequence after each reset) but cross-run determinism only with `SCOTCH_randomSeed` first
  or a fixed-seed build. The CLAUDE.md rule "always reset before randomized operations" is
  consistent with the global-`intranddat` design: all default contexts share one stream.
- **Never call `SCOTCH_randomVal` with `randmax <= 0`** (finding 2: SIGFPE kills the Python
  process) and call `SCOTCH_randomReset`/`SCOTCH_randomSeed` at least once before it
  (finding 3: otherwise all draws are 0). Cheap to guard in the ctypes wrapper.
- **Memory ownership**: buffers Scotch returns that were built with `memAllocGroup` are one
  block — free only via the corresponding Scotch free routine / block base, never per-array.
  With `COMMON_MEMORY_TRACE` builds, pointers are skewed by a size header, so a foreign
  `free()` from Python on a Scotch pointer is corruption; always route frees through the
  library.
- **Thread safety of global state**: `intranddat`, the error-program-name buffer
  (common_error.c:63), and the parser's *output* trees are the global surface. The parser is
  reentrant, but two Python threads driving default-context Scotch calls share one PRNG with
  non-atomic state — concurrent calls are both nondeterministic and racy. Serialize Scotch calls
  or give each thread a `SCOTCH_Context` with a cloned generator (`SCOTCH_contextRandomClone`).
- **Error interposition**: libscotch.so leaves `SCOTCH_errorPrint`/`SCOTCH_errorPrintW`
  undefined and unsuffixed by design; PyScotch can interpose by pre-loading its own definitions
  (or a ctypes-exported C callback shim) *before* libscotcherr resolves them. This is the one
  place where the unsuffixed name is load-bearing, so suffix-fixing patches must not touch it.
- **Strategy strings from Python**: user-supplied strategy strings that fail to parse leak a
  little memory each attempt (finding 1). If PyScotch validates strategies in a
  retry-until-valid loop (e.g. hypothesis tests generating strategy strings), expect slow RSS
  growth; prefer validating syntax on the Python side or bounding retries.
