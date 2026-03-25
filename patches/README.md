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

**Auto-applied**: Automatically copied to `external/scotch/src/Makefile.inc` during `make check-submodule` if it doesn't exist.

## History

The `scotch-suffix-fixes.patch` that used to live here was merged upstream in Scotch v7.0.11
(commit `f7cd80c` — "Bugfix: add missing suffix renaming macros [report C. Pellegrini]").
It fixed missing `SCOTCH_NAME_SUFFIX` macros for `SCOTCH_NUM_MPI`, `SCOTCH_Dmesh`, and 10 `SCOTCH_dmesh*` functions.
