"""
NOT PORTED: external/scotch/src/check/test_scotch_context.c

Context management with threading - INTERNAL THREADING API

REASON FOR NOT PORTING:
While the public API includes some context functions (SCOTCH_contextInit,
SCOTCH_contextExit, SCOTCH_contextBindGraph, SCOTCH_contextThreadSpawn, etc.),
this test file tests Scotch's INTERNAL threading implementation.

The test uses internal functions not exposed in scotch.h:
- contextThreadLaunch() - internal thread worker launch
- contextThreadNbr() - internal thread count query
- contextIntRandVal() - internal per-context RNG
- ThreadDescriptor - internal threading structure
- Direct access to internal Graph structure fields (grafptr->vertnbr)

The test includes custom worker functions (scotchGraphDoUsefulStuff, scotchSplit)
that use Scotch's internal threading API to verify that contexts properly manage
thread-local state and can split contexts across thread groups.

While the public context API (SCOTCH_contextInit, SCOTCH_contextThreadSpawn, etc.)
could be tested, this specific C test focuses on verifying the internal threading
implementation details that PyScotch users don't directly interact with.

If you need to use contexts in PyScotch:
- Use SCOTCH_contextInit/Exit for basic context management
- Use SCOTCH_contextBindGraph to bind contexts to graphs
- Threading is handled internally by PT-Scotch when using parallel variants
- External Python threading (e.g., with threading or multiprocessing modules)
  should not be mixed with PT-Scotch's internal threading
"""

# No tests - this file documents why test_scotch_context.c is not ported
