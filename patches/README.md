# Scotch Patches

This directory contains temporary patches for the Scotch library until fixes are merged upstream.

## scotch-suffix-fixes.patch

**Status**: Temporary (will be fixed in official Scotch release)

**Description**: Fixes 3 bugs in Scotch's `SCOTCH_NAME_SUFFIX` mechanism that caused symbol name collisions when loading both 32-bit and 64-bit variants simultaneously.

**The Problem**:

Building with suffixes worked fine, but when loading BOTH 32-bit and 64-bit variants in the same process, there were symbol name collisions because some symbols weren't getting suffixed. This prevented multi-variant loading.

**Bugs Fixed**:

1. **Missing `SCOTCH_NUM_MPI` constant macro** (line 270)
   - Without fix: Constant has same name in both variants → collision
   - Fix: Added `#define SCOTCH_NUM_MPI SCOTCH_NAME_PUBLIC (SCOTCH_NUM_MPI)`
   - Result: Becomes `SCOTCH_NUM_MPI_32` and `SCOTCH_NUM_MPI_64`

2. **Missing `SCOTCH_Dmesh` type macro** (line 290)
   - Without fix: Type has same name in both variants → collision
   - Fix: Added `#define SCOTCH_Dmesh SCOTCH_NAME_PUBLIC (SCOTCH_Dmesh)`
   - Result: Becomes `SCOTCH_Dmesh_32` and `SCOTCH_Dmesh_64`

3. **Missing 10 `SCOTCH_dmesh*` function macros** (lines 1247-1256)
   - Without fix: Functions have same names in both variants → collision
   - Fix: Added macros for all 10 dmesh functions:
     - `SCOTCH_dmeshAlloc` → `SCOTCH_dmeshAlloc_32` / `SCOTCH_dmeshAlloc_64`
     - `SCOTCH_dmeshBuildAdm`
     - `SCOTCH_dmeshData`
     - `SCOTCH_dmeshDgraphDual`
     - `SCOTCH_dmeshExit`
     - `SCOTCH_dmeshFree`
     - `SCOTCH_dmeshInit`
     - `SCOTCH_dmeshLoad`
     - `SCOTCH_dmeshSize`
     - `SCOTCH_dmeshSizeof`

**Impact**: Without these fixes, loading both 32-bit and 64-bit Scotch variants in the same process causes symbol collisions. With the fixes, all symbols get proper suffixes and all 4 variants (32/64-bit × sequential/parallel) can coexist peacefully.

**File Modified**: `external/scotch/src/libscotch/module.h`

**Upstream Status**: Reported to Scotch maintainers. Will be fixed in future release.

## How the Patch is Applied

The patch is automatically applied during the build process by the Makefile:

1. `make check-submodule` - Initializes git submodule if needed
2. Patch is applied to `external/scotch/src/libscotch/module.h`
3. `make build-32` or `make build-64` - Builds Scotch with suffix flags

The patch application is idempotent - it can be safely applied multiple times.

## Removing the Patch

Once these fixes are merged into the official Scotch release and the submodule is updated:

1. Remove `patches/scotch-suffix-fixes.patch`
2. Remove patch application logic from `Makefile`
3. Update `external/scotch` submodule to new version
4. Update this README

## Testing

To verify the patch works:

```bash
# Clean build
make clean

# Initialize submodule and apply patch
make check-submodule

# Build all variants
make build-all

# Verify all 4 variants built
ls -lh scotch-builds/lib32/libscotch.so scotch-builds/lib32/libptscotch.so
ls -lh scotch-builds/lib64/libscotch.so scotch-builds/lib64/libptscotch.so

# Run tests
pytest tests/ -v
```

All tests should pass (93 passed, 4 skipped).
