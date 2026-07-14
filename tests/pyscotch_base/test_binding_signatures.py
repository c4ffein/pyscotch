"""
Verify ctypes bindings in pyscotch.libscotch against the Scotch C headers.

For every function declared in libscotch's binding table, this parses the
prototype out of the exact scotch.h/ptscotch.h the loaded libraries were
built from, and checks:

- the C function actually exists in the header (no bindings to ghosts),
- the C symbol actually exists in the loaded library,
- the argument count matches,
- every ctypes argtype is compatible with the C parameter type,
- the ctypes restype is compatible with the C return type.

This is the machine check that the bindings cannot silently drift from the
Scotch version in the submodule. Headers ship in scotch-builds/inc{32,64}
(development layout); the test skips on installed wheels where headers are
not available.
"""

import ctypes
import re
from ctypes import POINTER, c_char_p, c_double, c_int, c_void_p
from pathlib import Path

import pytest

from pyscotch import libscotch as lib

INT_SIZE = lib.get_scotch_int_size()
INC_DIR = Path(__file__).resolve().parents[2] / "scotch-builds" / f"inc{INT_SIZE}"

pytestmark = pytest.mark.skipif(
    not INC_DIR.exists(),
    reason="Scotch headers not available (installed wheel?)",
)

# Matches single-line prototypes like:
#   int    SCOTCH_graphInit_64  (SCOTCH_Graph_64 * const);
#   SCOTCH_Num_64  SCOTCH_graphBase_64  (SCOTCH_Graph_64 * const, const SCOTCH_Num_64);
_PROTO_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_ ]*?(?:\s*\*)?)\s+(SCOTCH_[A-Za-z0-9_]+)\s*\(([^)]*)\)\s*;",
    re.MULTILINE,
)

_SUFFIX_RE = re.compile(r"_(?:32|64)$")

_STRUCTS = {
    "SCOTCH_Graph": lib.SCOTCH_Graph,
    "SCOTCH_Mesh": lib.SCOTCH_Mesh,
    "SCOTCH_Strat": lib.SCOTCH_Strat,
    "SCOTCH_Arch": lib.SCOTCH_Arch,
    "SCOTCH_Mapping": lib.SCOTCH_Mapping,
    "SCOTCH_Ordering": lib.SCOTCH_Ordering,
    "SCOTCH_Geom": lib.SCOTCH_Geom,
    "SCOTCH_Context": lib.SCOTCH_Context,
    "SCOTCH_Dgraph": lib.SCOTCH_Dgraph,
    "SCOTCH_Dmapping": lib.SCOTCH_Dmapping,
    "SCOTCH_Dordering": lib.SCOTCH_Dordering,
    "SCOTCH_ArchDom": None,  # not wrapped by pyscotch
}

_SCALARS = {
    "int": c_int,
    "double": c_double,
    "SCOTCH_Num": lib.SCOTCH_Num,
    "SCOTCH_Idx": lib.SCOTCH_Idx,
    "SCOTCH_GraphPart2": lib.SCOTCH_GraphPart2,
    "unsigned char": ctypes.c_ubyte,
}


def _parse_headers():
    """Parse {base_name: (return_decl, params_decl)} from the variant headers."""
    headers = ["scotch.h"]
    if lib.is_parallel():
        headers.append("ptscotch.h")
    protos = {}
    for header in headers:
        text = (INC_DIR / header).read_text()
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # strip comments
        for ret, name, params in _PROTO_RE.findall(text):
            base_name = _SUFFIX_RE.sub("", name)
            protos[base_name] = (ret.strip(), params.strip())
    return protos


def _parse_c_type(decl):
    """Reduce a C parameter/return declaration to (base_type, pointer_depth)."""
    ptr = decl.count("*")
    words = [w for w in decl.replace("*", " ").split() if w != "const"]
    base = _SUFFIX_RE.sub("", " ".join(words))
    return base, ptr


def _acceptable_ctypes(base, ptr):
    """Set of ctypes objects compatible with a C type, or None if unhandled."""
    if base == "void":
        return {None} if ptr == 0 else {c_void_p}
    if base == "char":
        # Both c_char_p and c_void_p are ABI-correct for char*
        return {c_char_p, c_void_p} if ptr else None
    if base == "FILE":
        return {c_void_p}
    if base == "MPI_Comm":
        # Opaque handle: pointer under OpenMPI, int under MPICH.
        # pyscotch passes it as void* both by value and by address.
        return {c_void_p}
    if base in _STRUCTS:
        struct = _STRUCTS[base]
        if struct is None:
            return None
        return {POINTER(struct)} if ptr == 1 else None
    if base in _SCALARS:
        scalar = _SCALARS[base]
        if ptr == 0:
            return {scalar}
        if ptr == 1:
            return {POINTER(scalar)}
        if ptr == 2:
            return {POINTER(POINTER(scalar))}
    return None


PROTOS = _parse_headers()


def test_headers_parsed():
    """The parser must find a substantial number of prototypes."""
    assert len(PROTOS) > 100


def test_every_declared_binding_exists_in_header():
    """Every function in the binding table must exist in the Scotch headers."""
    ghosts = sorted(name for name in lib._DECLARED_BINDINGS if name not in PROTOS)
    assert ghosts == [], f"Bindings declared for functions absent from headers: {ghosts}"


def test_every_declared_binding_exists_in_library():
    """Every function in the binding table must resolve in the loaded .so."""
    assert lib._MISSING_BINDINGS == []


def test_binding_signatures_match_headers():
    """Arg counts, argtypes and restype must match the header prototypes."""
    errors = []
    for name, (restype, argtypes) in sorted(lib._DECLARED_BINDINGS.items()):
        if name not in PROTOS:
            continue  # reported by test_every_declared_binding_exists_in_header
        ret_decl, params_decl = PROTOS[name]

        accept = _acceptable_ctypes(*_parse_c_type(ret_decl))
        if accept is None:
            errors.append(f"{name}: unhandled C return type '{ret_decl}'")
        elif restype not in accept:
            errors.append(f"{name}: restype {restype} != header '{ret_decl}'")

        params = [] if params_decl in ("", "void") else params_decl.split(",")
        if len(params) != len(argtypes):
            errors.append(f"{name}: {len(argtypes)} argtypes declared, header has {len(params)}")
            continue
        for i, (param, argtype) in enumerate(zip(params, argtypes)):
            accept = _acceptable_ctypes(*_parse_c_type(param))
            if accept is None:
                errors.append(f"{name} arg {i}: unhandled C type '{param.strip()}'")
            elif argtype not in accept:
                errors.append(f"{name} arg {i}: argtype {argtype} != header '{param.strip()}'")
    assert errors == [], "\n" + "\n".join(errors)
