"""
NOT PORTED: external/scotch/src/check/test_multilib.c

Multi-library support test - BLOCKED BY FILE* API

REASON FOR NOT PORTING:
This test uses SCOTCH_graphLoad() which requires FILE* pointers. Python ctypes
cannot safely handle FILE* pointers.

The test verifies that multiple Scotch libraries (32-bit/64-bit variants) can
coexist in the same process, loading graphs and performing operations with
each variant.

PyScotch already supports multi-variant loading (see pyscotch/libscotch.py's
multi-variant architecture), but the C test infrastructure for verifying this
requires FILE* operations.

See QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4 for the FILE* problem.
"""

# No tests - blocked by FILE* pointer limitations
