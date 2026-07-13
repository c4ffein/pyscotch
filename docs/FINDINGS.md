# Findings — 2026-07-12 production-readiness pass

Everything discovered while hardening PyScotch (signature verification, test
expansion, Scotch 7.0.12 validation). Two categories: bugs that were **ours**
(fixed the same day) and issues in **upstream Scotch** (reported in
[QUESTIONS_FOR_SCOTCH_TEAM_2.md](QUESTIONS_FOR_SCOTCH_TEAM_2.md)).

## Upstream Scotch — see QUESTIONS_FOR_SCOTCH_TEAM_2.md for full write-ups

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | `SCOTCH_memFree` missing from module.h rename table → exported unsuffixed while the suffixed header declares `SCOTCH_memFree_64` (7.0.11 and 7.0.12) | Link failure for C users of suffixed builds | Reported; PyScotch works around it |
| 2 | `SCOTCH_meshBuildElem` (new in 7.0.12) missing from module.h rename table → **7.0.12 does not build at all with `SCOTCH_RENAME_ALL`** | Build regression | Reported; verified 2-line fix in `patches/scotch-7.0.12-rename-all-fix.patch` |
| 3 | `SCOTCH_contextOptionSetNum` switches on the option *value* instead of the option *index* (`library_context.c`, 7.0.11) → the documented DETERMINISTIC→RANDOMFIXEDSEED cascade never fires; values ≥ 2 wrongly rejected | API misbehavior | Reported with Python repro |

With fix #2 applied, PyScotch's full suite passes against Scotch 7.0.12 on all
four variants — compatibility itself is fine.

## PyScotch bugs (all fixed 2026-07-12, caught by `tests/pyscotch_base/test_binding_signatures.py`)

| Binding | Bug | Real-world impact |
|---------|-----|-------------------|
| `SCOTCH_meshBuild` | argtypes missing 1 of 12 parameters | trailing args escaped ctypes validation |
| `SCOTCH_meshData` | argtypes had 10 of 13 parameters, wrong layout | declared-only; would have corrupted on first use |
| `SCOTCH_dgraphData` | argtypes had 16 of 17, pointer groups misaligned | trailing args escaped validation |
| `SCOTCH_version` | declared `SCOTCH_Num*`, C wants `int*` | worked only by little-endian luck |
| `SCOTCH_memCur` / `SCOTCH_memMax` | restype `c_long`, C returns `SCOTCH_Idx` | wrong-width reads on the 32-bit variant |
| `dgraph.data()` commptr | 4-byte `c_int` buffer receiving an `MPI_Comm` | **memory corruption** under OpenMPI (8-byte handle) |

Root cause of all of the above: ctypes only type-checks the declared argtypes
prefix, so a too-short argtypes list silently skips validation of trailing
arguments — the callers were passing correct arguments into wrongly-declared
bindings. The signature test now diff-checks every binding against the parsed
Scotch headers in CI, so this class of bug cannot recur.

## Process findings

- Grep-based "which bindings are untested" analysis overcounted 34 untested
  wrappers; runtime tracing of `libscotch._get_func` showed only 4 were truly
  unexercised. Coverage claims should come from tracing, not grep.
- `README.md` documents `PYSCOTCH_INT_SIZE`/`PYSCOTCH_PARALLEL` defaults as
  64/1 but `libscotch.py` defaults to 32/0 — **still undecided**.
