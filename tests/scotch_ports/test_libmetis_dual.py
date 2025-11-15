"""
NOT PORTED: external/scotch/src/check/test_libmetis_dual.c

METIS dual graph compatibility - BLOCKED BY FILE* API

REASON FOR NOT PORTING:
This test uses SCOTCH_graphLoad() which requires FILE* pointers. Python ctypes
cannot safely handle FILE* pointers.

The test loads a graph from file and tests METIS dual graph partitioning
functions provided by libscotchmetis.

See QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4 for the FILE* problem.
"""

# No tests - blocked by FILE* pointer limitations
