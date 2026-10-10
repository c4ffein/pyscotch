# Scotch Build Configuration

This directory contains configuration files for building Scotch.

## Makefile.inc.default

**Purpose**: Default build configuration for Scotch

**Description**: Scotch doesn't come with a `Makefile.inc` by default. This file provides a working configuration for Linux with:
- GCC for sequential compilation (`CCS = gcc`)
- MPI (mpicc) for parallel PT-Scotch (`CCP = mpicc`, `CCD = mpicc`)
- Shared library support (`.so`)
- Compression support (zlib)
- Thread support (pthread)

**Auto-applied**: Automatically copied to `external/scotch/src/Makefile.inc` during `make check-submodule` (into the disposable patched copy) if it doesn't exist.

## Patch classes

Bundled patches (shipped in this directory (`pyscotch/_scotch_patches/`), applied by `pyscotch
scotch build` and catalogued in `pyscotch/scotch_build.py`) come in two
classes with different rules:

- **Quickfix** (`_PATCHES`): fixes a BUILD break (the version does not
  compile under PyScotch's suffixed build). Applied automatically; skipped
  only by `--pristine`. Example: `scotch-7.0.12-rename-all-fix.patch`.
- **Behavioral** (`_BEHAVIORAL_PATCHES`): changes the library's RESULTS.
  Never applied silently — the build asks per patch (default yes), a
  non-interactive build skips with a note, and
  `--auto-allow-behavioral-patches` pre-approves. Example:
  `scotch-7.0.16-bgraph-bipart-gg-determinism.patch` (restores
  reproducibility in the threaded `bgraphBipartGg()`; see the 2026-10-08
  entry in `docs/QUESTIONS_FOR_SCOTCH_TEAM.md`).

Policy: every behavioral patch is **temporary** — it must have a
`QUESTIONS_FOR_SCOTCH_TEAM.md` entry (it doubles as the proposed upstream
fix) and is retired the day upstream ships one. Wheels and the repo's own
default builds always keep pristine upstream behavior.

## History

The `scotch-suffix-fixes.patch` that used to live here was merged upstream in Scotch v7.0.11
(commit `f7cd80c` — "Bugfix: add missing suffix renaming macros [report C. Pellegrini]").
It fixed missing `SCOTCH_NAME_SUFFIX` macros for `SCOTCH_NUM_MPI`, `SCOTCH_Dmesh`, and 10 `SCOTCH_dmesh*` functions.
