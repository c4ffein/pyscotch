"""
NOT PORTED: external/scotch/src/check/test_common_thread.c

Common threading utilities - INTERNAL THREADING API

REASON FOR NOT PORTING:
This test file tests Scotch's internal threading primitives, which are NOT
part of the public API exposed in scotch.h.

The test uses these internal functions from common_thread.h:
- threadLaunch(&contdat, func, data) - Launch thread group
- threadBarrier(descptr) - Thread barrier synchronization
- threadReduce(descptr, data, size, func, ...) - Thread reduction
- threadScan(descptr, data, size, func, ...) - Thread scan operation
- threadContextExit(&contdat) - Clean up thread context

These are internal threading primitives that Scotch uses to implement
parallel algorithms (PT-Scotch). They are implementation details not
exposed to external users.

PyScotch bindings focus on the public API in scotch.h. Threading is
handled internally by Scotch when using PT-Scotch variants. Users don't
directly interact with these threading primitives.

If you need to test parallel behavior, use the public PT-Scotch functions
(SCOTCH_dgraph* family) which use these threading primitives internally.
"""

# No tests - this file documents why test_common_thread.c is not ported
