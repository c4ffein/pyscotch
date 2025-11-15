"""
NOT PORTED: external/scotch/src/check/test_scotch_arch_deco.c

Architecture decomposition - BLOCKED BY FILE* API

REASON FOR NOT PORTING:
This test uses SCOTCH_archLoad() which requires FILE* pointers. Python ctypes
cannot safely handle FILE* pointers.

The test loads target architectures from files and tests decomposition/matching
operations using the PUBLIC architecture API (SCOTCH_archInit, SCOTCH_archLoad, etc.).

The core functionality uses public API, but file loading infrastructure is blocked.

See QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4 for the FILE* problem.
"""

# No tests - blocked by FILE* pointer limitations
