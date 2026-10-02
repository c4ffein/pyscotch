# Instructions for Claude AI

## Dependency management
- We're using `uv`, so don't use `pip` but `uv pip`

## Scotch Submodule Setup
- At the start of each session, initialize the scotch submodule: `git submodule update --init --recursive`
- If this fails, inform the user they likely forgot to grant access to `gitlab.inria.fr` in their environment configuration.

## Testing strategy
- When importing a test from Scotch, maximize the similarity with the existing test. NEVER PUT THE DUST UNDER THE RUG.
- ALWAYS KEEP THE EXACT SAME ASSERTIONS. THE TESTS **NEVER** ARE THE PROBLEM. DON'T TRY TO MODIFY THE TEST. FIX THE IMPLEMENTATION.
- But WHEN YOU THINK A TEST IS INCOMPLETE, and COULD BE MORE COMPREHENSIVE, you can add notes to the `docs/QUESTIONS_FOR_SCOTCH_TEAM.md` file! We'll get back to them so they can potentially improve the tests with your help :)

## GENERAL ADVICE - PLEASE TAKE NOTE
- YOU ARE NOT SUPPOSED TO BE POSITIVE WHEN SOMETHING FAILS.
- IF YOU CAN'T FIX SOMETHING, YOU JUST STOP AND ASK THE USER TO LOOK INTO IT.

## Generated docs API catalog (committed) — regenerate on any public-API change
- `docs/site/api_data.json` is generated from the live API and **committed**.
  If you add/remove/rename a public method, change a signature, or edit a
  method's one-line summary, you MUST regenerate it — else the "Verify docs
  API data" CI job fails on the stale file. This is easy to forget because the
  code change works fine; only CI catches it.
- Regenerate with **`make docs-api`** (not a bare `python docs/site/gen_api.py
  --dump`). The catalog embeds the loaded Scotch version and the set of
  available *parallel* symbols, so it is environment-sensitive: it must be
  generated with Python >= 3.14 (the uv `.venv`, which has the deps — a bare
  `python3.14` does not), a **fresh 64-bit build**, and `PYSCOTCH_PARALLEL=1`.
  `make docs-api` pins exactly that (mirroring CI); a hand-run against a stray
  `~/.local` build or with `PYSCOTCH_PARALLEL=0` produces a wrong file (wrong
  version / undercounted symbols) that is still stale in CI.
- **Always GENERATE the file — never hand-edit it to match CI's failure diff.**
  Faking the artifact is exactly the dust-under-the-rug this repo forbids
  (even when the diff looks obviously right). If you genuinely cannot run
  `make docs-api` (no 3.14 env, no MPI build), STOP and ask the user to run it
  and commit the result — do not guess or patch the JSON by hand.

## Scotch API Knowledge

### Random State Management
- **Always call `SCOTCH_randomReset()` before randomized operations** (coloring, partitioning, etc.)
- Without reset, the pseudorandom generator state carries over between calls, leading to non-deterministic and sometimes invalid results
- Determinism in Scotch depends on compilation flags and environment variables

### Opaque Structure Sizing
- **Always use `SCOTCH_*Sizeof()` functions** to get structure sizes dynamically (e.g., `SCOTCH_dgraphSizeof()`)
- Never use fixed buffer sizes - structure sizes differ between 32-bit and 64-bit variants
- Sizes are specified in doubles for alignment purposes

### Algorithm Characteristics
- `SCOTCH_graphColor` is a **greedy heuristic** - don't expect optimal colorings
- When `SCOTCH_dgraphCoarsen` returns 1 (cannot coarsen), the coarse graph is in an **invalid state** - don't call `SCOTCH_dgraphExit` on it
- Only call `SCOTCH_*Exit` functions when the corresponding operation **succeeded**

### Error Handling Pattern
- Return value 0 = success
- Return value 1 = operation not possible (e.g., graph too small to coarsen) - not an error, but output may be invalid
- Return value 2+ = actual error

### Init/Exit Pattern
- User must call `SCOTCH_*Init` externally before passing structures to operations (e.g., `SCOTCH_dgraphInit` before `SCOTCH_dgraphCoarsen`)
- Scotch cleans internal state at the start of routines, but expects initialized structures
- Only call `SCOTCH_*Exit` on structures where the operation succeeded

### Reference Implementation
- **ScotchPy** (official bindings) is in `scotchpy/` directory
  - check it for correct patterns when unsure
  - if it is not present, ask the user to get it for you
- Example: `scotchpy/scotchpy/dgraph.py` shows proper dynamic sizing with `SCOTCH_dgraphSizeof()`

### C Test Limitations
- Scotch's C tests often only verify return codes, not output validity
- Don't assume "C test passes" = "behavior is correct"
- PyScotch Hypothesis tests (`tests/hypothesis/`) provide stronger property-based validation
