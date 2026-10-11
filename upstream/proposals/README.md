# Proposed patches

Patches written for upstream that PyScotch does not apply itself. Each file
pairs with an entry in `../QUESTIONS_FOR_SCOTCH_TEAM.md` giving the mechanism
and a C-only repro.

Patches PyScotch *does* apply are catalogued in `pyscotch/_scotch_patches/`
and are not duplicated here; those that are also proposals upstream:

- `scotch-7.0.16-bgraph-bipart-gg-determinism.patch` — restores
  reproducibility and best-pass selection in the multi-threaded
  `bgraphBipartGg()` (7.0.16 regression, upstream `7a934a8`). Shipped as a
  confirmed-only behavioral patch; proposed upstream 2026-10-08.
