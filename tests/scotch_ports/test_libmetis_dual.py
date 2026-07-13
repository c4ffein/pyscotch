"""
NOT PORTED: external/scotch/src/check/test_libmetis_dual.c

METIS dual graph compatibility - MISSING BINDINGS

REASON FOR NOT PORTING:
PyScotch does not provide bindings for libscotchmetis (the METIS compatibility
layer). The FILE* limitation that originally blocked this has been resolved
via the c_fopen() compatibility shim, but porting this test would still
require creating ctypes bindings for METIS_MeshToDual(), METIS_PartMeshDual(),
etc.
"""

# No tests - missing libscotchmetis bindings
