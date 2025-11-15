"""
NOT PORTED: external/scotch/src/check/test_libmetis.c

METIS compatibility layer - BLOCKED BY FILE* API

REASON FOR NOT PORTING:
This test uses SCOTCH_graphLoad() which requires FILE* pointers. Python ctypes
cannot safely handle FILE* pointers.

The test loads a graph from file and tests the METIS compatibility API provided
by libscotchmetis. This compatibility layer provides METIS-compatible function
signatures (METIS_PartGraphKway, METIS_PartGraphRecursive, etc.) implemented
using Scotch internally.

The METIS compatibility functions use the PUBLIC API, but the test infrastructure
(graph file loading) is blocked by FILE* limitations.

Note: PyScotch doesn't currently provide METIS compatibility bindings. Users
needing METIS compatibility should use the C library directly or consider using
native Scotch functions.

See QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4 for the FILE* problem.
"""

# No tests - blocked by FILE* pointer limitations
