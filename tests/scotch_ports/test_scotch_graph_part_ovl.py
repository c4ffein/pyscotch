"""
NOT PORTED: external/scotch/src/check/test_scotch_graph_part_ovl.c

Graph partitioning with overlap - BLOCKED BY FILE* API

REASON FOR NOT PORTING:
This test uses SCOTCH_graphLoad() which requires FILE* pointers. Python ctypes
cannot safely handle FILE* pointers.

The test loads a graph from file and tests overlapping partitioning using
SCOTCH_graphPartOvl(), which computes graph partitions with overlapping boundaries.

The core functionality (overlapping partitioning) uses the PUBLIC API, but
test infrastructure (file loading) is blocked by FILE* limitations.

See QUESTIONS_FOR_SCOTCH_TEAM.md Issue #4 for the FILE* problem.
"""

# No tests - blocked by FILE* pointer limitations
