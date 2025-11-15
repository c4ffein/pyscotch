"""
NOT PORTED: external/scotch/src/check/test_libesmumps.c

ESMUMPS compatibility layer - BLOCKED BY FILE* API

REASON FOR NOT PORTING:
This test uses SCOTCH_graphLoad() which requires FILE* pointers. Python ctypes
cannot safely handle FILE* pointers.

The test loads a graph from file and tests the ESMUMPS compatibility API
provided by libesmumps. This compatibility layer provides ESMUMPS-compatible
function signatures implemented using Scotch internally.

The ESMUMPS compatibility functions use the PUBLIC API, but the test
infrastructure (graph file loading) is blocked by FILE* limitations.

See QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4 for the FILE* problem.
"""

# No tests - blocked by FILE* pointer limitations
