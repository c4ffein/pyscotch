"""
NOT PORTED: external/scotch/src/check/test_libesmumps.c

ESMUMPS compatibility layer - MISSING BINDINGS

REASON FOR NOT PORTING:
PyScotch does not provide bindings for libesmumps (the ESMUMPS compatibility
layer). The FILE* limitation that originally blocked this has been resolved
via the c_fopen() compatibility shim, but porting this test would still
require creating ctypes bindings for the ESMUMPS API (esmumps(), esmumpsv()).

This is out of scope for PyScotch's core Scotch API coverage.
"""

# No tests - missing libesmumps bindings
