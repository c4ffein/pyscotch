# Instructions for Claude AI

## Dependency management
- We're using `uv`, so don't use `pip` but `uv pip`

## Scotch Submodule Setup
- At the start of each session, initialize the scotch submodule: `git submodule update --init --recursive`
- If this fails, inform the user they likely forgot to grant access to `gitlab.inria.fr` in their environment configuration.

## Testing strategy
- When importing a test from Scotch, maximize the similarity with the existing test. NEVER PUT THE DUST UNDER THE RUG.
- ALWAYS KEEP THE EXACT SAME ASSERTIONS. THE TESTS **NEVER** ARE THE PROBLEM. DON'T TRY TO MODIFY THE TEST. FIX THE IMPLEMENTATION.
- But WHEN YOU THINK A TEST IS INCOMPLETE, and COULD BE MORE COMPREHENSIVE, you can add notes to the `QUESTIONS_FOR_SCOTCH_TEAM.md` file! We'll get back to them so they can potentially improve the tests with your help :)

## GENERAL ADVICE - PLEASE TAKE NOTE
- YOU ARE NOT SUPPOSED TO BE POSITIVE WHEN SOMETHING FAILS.
- IF YOU CAN'T FIX SOMETHING, YOU JUST STOP AND ASK THE USER TO LOOK INTO IT.

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
- **ScotchPy** (official bindings) is in `scotchpy/` directory - check it for correct patterns when unsure
- Example: `scotchpy/scotchpy/dgraph.py` shows proper dynamic sizing with `SCOTCH_dgraphSizeof()`

### C Test Limitations
- Scotch's C tests often only verify return codes, not output validity
- Don't assume "C test passes" = "behavior is correct"
- PyScotch Hypothesis tests (`tests/hypothesis/`) provide stronger property-based validation
