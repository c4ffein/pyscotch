# Public vs Internal API Analysis

## Overview

Some Scotch C tests use **internal APIs** (from `module.h` and `common.h`) that are not exposed to external users, while others use **public APIs** (from `scotch.h`) that we should port. This document analyzes which tests fall into which category.

## Key Findings

### Internal vs Public API Distinction

**Internal API characteristics:**
- Declared in `src/libscotch/module.h` and `src/libscotch/common.h`
- Uses `SCOTCH_NAME_INTERN` macro for name mangling
- Takes explicit context arguments (e.g., `IntRandContext *`)
- Allows multiple independent contexts
- NOT meant for external library users

**Public API characteristics:**
- Declared in `include/scotch.h`
- Stable ABI across versions
- Uses global contexts internally
- Documented and supported for external use

## Test-by-Test Analysis

### ✅ test_common_random.c - **INTERNAL API** (Should NOT port)

**Includes:**
```c
#include "../libscotch/module.h"
#include "../libscotch/common.h"
#include "scotch.h"
```

**Functions used:**
- ❌ `intRandInit(&intranddat)` - INTERNAL (common.h line 440)
- ❌ `intRandVal(&intranddat, INTVALMAX)` - INTERNAL (common.h line 446)
- ❌ `intRandReset(&intranddat)` - INTERNAL (common.h line 443)
- ❌ `intRandSave(&intranddat, fileptr)` - INTERNAL (common.h line 444)
- ❌ `intRandLoad(&intranddat, fileptr)` - INTERNAL (common.h line 441)
- ❌ `errorProg()`, `errorPrint()` - INTERNAL error handling

**Public equivalents exist:**
- ✅ `SCOTCH_randomReset()` - PUBLIC (scotch.h line 354)
- ✅ `SCOTCH_randomVal(SCOTCH_Num)` - PUBLIC (scotch.h line 356)
- ✅ `SCOTCH_randomSeed(SCOTCH_Num)` - PUBLIC (scotch.h line 355)
- ✅ `SCOTCH_randomSave(FILE *)` - PUBLIC (scotch.h line 352)
- ✅ `SCOTCH_randomLoad(FILE *)` - PUBLIC (scotch.h line 351)

**Key difference:** Internal API takes `IntRandContext *` allowing multiple independent RNG contexts. Public API uses a single global context.

**Recommendation:** **SKIP this test** - it tests internal implementation details. We already have equivalent tests using the public API in `tests/scotch_ports/test_common_random.py`.

---

### ⚠️  test_scotch_graph_dump.c - **MIXED API** (Should port, but blocked)

**Includes:**
```c
#include "../libscotch/module.h"
#include "../libscotch/common.h"
#include "scotch.h"
```

**Functions used:**
- ✅ `SCOTCH_graphInit()` - PUBLIC (scotch.h line 248)
- ✅ `SCOTCH_graphSave()` - PUBLIC (scotch.h line 252)
- ✅ `SCOTCH_graphExit()` - PUBLIC (scotch.h line 249)
- ✅ `SCOTCH_errorProg()`, `SCOTCH_errorPrint()` - PUBLIC error handling
- ❌ `testGraphBuild()` - GENERATED at build time (see line 116 comment)

**Recommendation:** **PORT this test** - uses public API. However, it's currently blocked by FILE* segfault issues (QUESTIONS_FOR_SCOTCH_TEAM.md #4). The `testGraphBuild()` function is auto-generated during Scotch build and pasted into the test file.

---

### ✅ test_scotch_graph_color.c - **PUBLIC API** (Already ported ✅)

**Status:** Successfully ported! All functions used are in public API.

---

### ✅ test_scotch_graph_induce.c - **PUBLIC API** (Already ported ✅)

**Status:** Successfully ported! All functions used are in public API.

---

## Summary Table

| Test File | API Type | Should Port? | Status | Notes |
|-----------|----------|--------------|--------|-------|
| test_common_random.c | Internal | ❌ NO | Skipped | Uses `intRand*` internal API |
| test_scotch_graph_dump.c | Public | ✅ YES | ⚠️ Blocked | FILE* segfaults + testGraphBuild() |
| test_scotch_graph_color.c | Public | ✅ YES | ✅ Ported | 4/4 tests passing |
| test_scotch_graph_induce.c | Public | ✅ YES | ✅ Ported | 5/5 tests passing |

## Recommendations

### 1. Tests Using Internal APIs
**Do NOT port** tests that include `module.h` or `common.h` and use internal functions. These test implementation details not meant for external users.

**How to identify:**
- Check if test includes `"../libscotch/module.h"` or `"../libscotch/common.h"`
- Check if functions use lowercase naming (e.g., `intRandInit`, `errorProg`)
- Check if functions take context arguments not exposed in public API

### 2. Tests Using Public APIs
**DO port** tests that primarily use `SCOTCH_*` functions from `scotch.h`.

**Exception:** If the test requires FILE* operations (graph/mapping save/load), it's currently blocked by Python ctypes limitations (see QUESTIONS_FOR_SCOTCH_TEAM.md #4).

### 3. Verification Strategy
Before porting a test:

1. Read the C file includes section
2. If it includes internal headers (`module.h`, `common.h`), check what functions it uses
3. Search for those functions in `external/scotch/include/scotch.h`
4. If functions are NOT in scotch.h, skip the test
5. If functions ARE in scotch.h, proceed with porting

### 4. Update Porting Status
Update `PORTING_STATUS.md` with a new column indicating API type:

```markdown
| C File | Python File | Status | API Type | Notes |
|--------|-------------|--------|----------|-------|
| test_common_random.c | - | ⏭️ Skipped | Internal | Uses intRand* functions |
```

## Important Discovery: Most Tests Include Internal Headers

**Finding:** 23 out of 26 test files include `module.h` (internal header), but this doesn't mean they all use internal APIs!

```bash
# Tests that include module.h:
test_scotch_arch.c, test_scotch_arch_deco.c, test_scotch_context.c,
test_scotch_dgraph_*.c (5 tests), test_scotch_graph_*.c (9 tests),
test_common_*.c (3 tests), test_fibo.c, test_libmetis*.c (2 tests)

# Tests that DON'T include module.h:
test_libesmumps.c (not found or doesn't include)
test_multilib.c (not checked)
```

**Key insight:** Including `module.h`/`common.h` is common because:
1. Tests use utility functions like `errorProg()`, `errorPrint()`
2. Tests need access to internal types for verification
3. Tests may use `testGraphBuild()` and similar test-only functions

**But:** Many tests ONLY call public `SCOTCH_*` functions and can be ported!

**Examples:**
- ✅ `test_scotch_graph_color.c` - includes module.h, BUT only uses public API → **Successfully ported!**
- ✅ `test_scotch_graph_induce.c` - includes module.h, BUT only uses public API → **Successfully ported!**
- ❌ `test_fibo.c` - includes fibo.h, uses `fiboHeap*()` functions → **Internal data structure test, skip**
- ❌ `test_common_random.c` - uses `intRand*()` with context args → **Internal API test, skip**

## Revised Categorization Strategy

Instead of checking includes, check **actual function calls**:

### Category 1: Pure Public API (Should port)
Tests that ONLY call `SCOTCH_*` functions from scotch.h, even if they include module.h.

**Examples:**
- `SCOTCH_graphInit()`, `SCOTCH_graphCheck()`, `SCOTCH_graphColor()`
- `SCOTCH_graphInduceList()`, `SCOTCH_graphInducePart()`
- `SCOTCH_randomReset()`, `SCOTCH_randomVal()`

### Category 2: Internal API (Should NOT port)
Tests that call lowercase internal functions:

**Examples:**
- `intRandInit()`, `intRandVal()` - internal RNG with context
- `fiboHeapAdd()`, `fiboHeapDel()` - internal Fibonacci heap
- `graphBuild()`, `graphCheck()` - internal graph utilities (not `SCOTCH_*` versions)

### Category 3: Mixed (Evaluate case-by-case)
Tests using mostly public API but with some internal helpers:

**Examples:**
- Uses `SCOTCH_*` functions but also `testGraphBuild()` (generated test helper)
- Uses `SCOTCH_*` functions but internal verification functions

**Strategy:** Port the test using public API, skip or adapt internal parts.

## Confirmed Internal-Only Tests to Skip

Based on analysis:

1. ❌ **test_fibo.c** - Fibonacci heap data structure (internal)
2. ❌ **test_common_random.c** - Internal `intRand*()` API (we use public API instead)
3. ❌ **test_common_thread.c** - Likely internal threading utilities
4. ⚠️  **test_common_file_compress.c** - Need to check, might be internal file I/O

## Next Steps

1. **Review each unported test individually:**
   - Read the C file
   - List functions called (grep for `^\s+[a-z]` vs `^\s+SCOTCH_`)
   - Categorize as public/internal/mixed

2. **Update PORTING_STATUS.md** with findings

3. **Priority order for porting:**
   - Pure public API tests first
   - Mixed tests second (adapt as needed)
   - Skip internal tests entirely

4. **Create test stubs only for public API tests**

This approach ensures we're testing PyScotch's public API coverage without getting blocked by internal implementation tests.
