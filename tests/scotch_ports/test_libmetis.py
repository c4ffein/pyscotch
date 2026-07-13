"""
NOT PORTED: external/scotch/src/check/test_libmetis.c

METIS compatibility layer - MISSING BINDINGS

REASON FOR NOT PORTING:
PyScotch does not provide bindings for libscotchmetis (the METIS compatibility
layer). The FILE* limitation that originally blocked this has been resolved
via the c_fopen() compatibility shim, but porting this test would still
require creating ctypes bindings for the entire METIS API
(METIS_PartGraphKway, METIS_PartGraphRecursive, etc.).

Users needing METIS compatibility should use the C library directly or
consider using native Scotch functions.
"""

# No tests - missing libscotchmetis bindings
