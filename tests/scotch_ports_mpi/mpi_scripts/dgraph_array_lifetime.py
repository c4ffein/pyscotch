#!/usr/bin/env python3
"""
Array ownership across the Python/C boundary, for every Dgraph input method.

What Scotch does with the arrays it is given (external/scotch, 7.0.13):

- SCOTCH_dgraphBuild does NOT copy: dgraph_build.c:342-352 store the
  vertloctax, vendloctax, veloloctax, vlblloctax, edgeloctax and edloloctax
  pointers verbatim, and the graph reads through them for its whole life. So
  whatever Dgraph.build hands to Scotch must live as long as the Dgraph --
  including any copy PyScotch itself makes to convert a dtype or compact a
  strided view. (When vertex labels are given, dgraph_build.c additionally
  REWRITES the edge array in place, translating labels into global indices;
  this script uses identity labels so the rewrite is a no-op and the readback
  assertions stay exact.)
- SCOTCH_dgraphGrow / SCOTCH_dgraphBand re-use the seed (frontier) array as
  their breadth-first queue (dgraph_band_grow.c:84, "re-used as queue array"):
  it must hold vertlocnbr entries and its contents are clobbered.
- grow's partgsttab and build's edgegsttab are OUTPUT arrays Scotch fills in
  place (the latter during ghst()); converting them would send the results to
  a temporary, so a wrong-width / non-contiguous / non-numpy one must be
  refused before any Scotch call.
- redist's and induce_part's arrays are `const` inputs read during the call
  only (library_dgraph_redist.c:78-79, library_dgraph_induce.c:132).

How this script pins each of those, on a 40-vertex ring split over 2 ranks:

1. build() from Python lists, from arrays of the WRONG integer width (int32
   on a 64-bit build, int64 on a 32-bit one) and from non-contiguous strided
   views -- with ALL optional arrays (vendloctab, veloloctab, vlblloctab,
   edloloctab) -- then:
   - DETERMINISTIC ownership proof: the address Scotch reports through
     SCOTCH_dgraphData for every array equals the address of the array the
     Dgraph retained, which is C-contiguous and of the Scotch dtype;
   - the probabilistic proof too: every caller-side reference is dropped,
     the heap is churned with blocks of exactly the freed sizes, and every
     array is read back through Scotch and compared value by value;
   - check() passes; exit() and free() release the retained arrays.
2. edgegsttab, the real workflow: a correctly typed array is passed to
   build(), ghst() fills it in place (local neighbours map to their local
   index, ghosts to indices >= vertlocnbr), and Scotch holds that very
   address. Wrong width, a list, and a strided view are each refused with
   TypeError before any Scotch call.
3. grow(): a one-entry seed array (far shorter than vertlocnbr -- before the
   work-array fix this overflowed the heap and died in MPI_Finalize under
   some heap layouts) of either width grows the partition; the caller's seed
   array is byte-identical afterwards; the private work array has vertlocnbr
   entries, starts with the seeds, and Scotch demonstrably wrote queue
   entries past the seed count. partgsttab refusals as above; a declared
   seed count that exceeds the array, or is negative, raises ValueError.
4. band(), redist() and induce_part() from wrong-width AND strided inputs
   each produce a valid graph of the expected size.

Every refusal/validation path raises on all ranks identically, before any
collective call, so no rank is left waiting in MPI.

Run with: mpirun -np 2 python dgraph_array_lifetime.py
"""

import ctypes
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pyscotch import libscotch as lib
from pyscotch.dgraph import Dgraph
from pyscotch.mpi import mpi

RING = 40  # global vertices, split evenly across the 2 ranks
HEAP_JUNK = 12345678  # value the heap churn writes into reused blocks

# Order of Dgraph._build_arrays, and the matching SCOTCH_dgraphData field
BUILD_ARRAYS = (
    "vertloctab",
    "edgeloctab",
    "vendloctab",
    "veloloctab",
    "vlblloctab",
    "edgegsttab",
    "edloloctab",
)


def wrong_dtype():
    """An integer dtype that is NOT the loaded Scotch width (forces a copy)."""
    return np.int32 if lib.get_scotch_dtype() == np.int64 else np.int64


def address(ptr):
    """Integer address held by a ctypes POINTER(SCOTCH_Num)."""
    return ctypes.cast(ptr, ctypes.c_void_p).value


def read_back(ptr, count):
    """The `count` SCOTCH_Num values Scotch sees through `ptr`."""
    return [int(ptr[i]) for i in range(count)]


def local_ring(rank, size):
    """Every CSR array (global neighbour numbering) of this rank's ring slice.

    Labels are the global vertex numbers (identity), edge loads are symmetric
    (same value in both directions), vertex loads vary so a wrong readback
    cannot be mistaken for the right one.
    """
    n_loc = RING // size
    first = rank * n_loc
    vertloctab = [2 * i for i in range(n_loc + 1)]
    edgeloctab, edloloctab = [], []
    for i in range(first, first + n_loc):
        for j in ((i - 1) % RING, (i + 1) % RING):
            edgeloctab.append(j)
            edloloctab.append(1 + (min(i, j) + max(i, j)) % 5)
    return {
        "vertloctab": vertloctab,
        "vendloctab": vertloctab[1:],
        "veloloctab": [1 + (first + i) % 3 for i in range(n_loc)],
        "vlblloctab": [first + i for i in range(n_loc)],
        "edgeloctab": edgeloctab,
        "edloloctab": edloloctab,
    }


# Three ways to hand the arrays over that all force PyScotch to make a copy
def as_lists(values):
    return list(values)


def as_wrong_width(values):
    return np.array(values, dtype=wrong_dtype())


def as_strided_view(values):
    """Right dtype but non-contiguous: every other element of a doubled array."""
    return np.repeat(np.array(values, dtype=lib.get_scotch_dtype()), 2)[::2]


CONVERSIONS = (
    ("python lists", as_lists),
    ("wrong width", as_wrong_width),
    ("strided view", as_strided_view),
)


def fail(rank, msg):
    raise AssertionError(f"rank {rank}: {msg}")


# --------------------------------------------------------------------------
# 1. build(): ownership of every input array
# --------------------------------------------------------------------------


def build_from_temporaries(rank, size, convert):
    """Build a Dgraph from converted inputs that die when this returns."""
    arrays = local_ring(rank, size)
    dgraph = Dgraph()
    dgraph.build(
        convert(arrays["vertloctab"]),
        convert(arrays["edgeloctab"]),
        baseval=0,
        vendloctab=convert(arrays["vendloctab"]),
        veloloctab=convert(arrays["veloloctab"]),
        vlblloctab=convert(arrays["vlblloctab"]),
        edloloctab=convert(arrays["edloloctab"]),
    )
    return dgraph


def churn_heap(rank, size):
    """Reuse freed blocks of exactly the sizes build() may have freed."""
    n_loc = RING // size
    junk = []
    for _ in range(3000):
        for n in (n_loc + 1, n_loc, 2 * n_loc):
            junk.append(np.full(n, HEAP_JUNK, dtype=lib.get_scotch_dtype()))
            junk.append(np.full(n, HEAP_JUNK, dtype=wrong_dtype()))
    return junk


def scotch_pointers(dgraph):
    """The array pointers Scotch holds, keyed like BUILD_ARRAYS."""
    data = dgraph.data(
        want_vertloctab=True,
        want_vendloctab=True,
        want_veloloctab=True,
        want_vlblloctab=True,
        want_edgeloctab=True,
        want_edgegsttab=True,
        want_edloloctab=True,
    )
    return {name: data[name] for name in BUILD_ARRAYS}


def check_build_owns_its_arrays(rank, size, label, convert):
    dgraph = build_from_temporaries(rank, size, convert)
    dtype = lib.get_scotch_dtype()
    expected = local_ring(rank, size)

    # Deterministic proof: Scotch's pointers ARE the retained arrays
    retained = dict(zip(BUILD_ARRAYS, dgraph._build_arrays))
    pointers = scotch_pointers(dgraph)
    for name in expected:
        arr = retained[name]
        if not isinstance(arr, np.ndarray) or arr.dtype != dtype or not arr.flags.c_contiguous:
            fail(
                rank,
                f"[{label}] retained {name} is not a C-contiguous Scotch-dtype array: {arr!r}",
            )
        if address(pointers[name]) != arr.ctypes.data:
            fail(
                rank,
                f"[{label}] Scotch holds {name} at {address(pointers[name]):#x} but the Dgraph "
                f"retained an array at {arr.ctypes.data:#x}: the pointer dangles",
            )
    if retained["edgegsttab"] is not None:
        fail(rank, f"[{label}] no edgegsttab was passed but one is retained")

    # Probabilistic proof too: free everything caller-side, reuse the heap,
    # and read every array back through Scotch
    del retained, pointers
    junk = churn_heap(rank, size)  # noqa: F841 (must stay referenced)
    pointers = scotch_pointers(dgraph)
    for name, values in expected.items():
        seen = read_back(pointers[name], len(values))
        if seen != values:
            fail(
                rank,
                f"[{label}] Scotch reads garbage for {name} after build()'s temporaries were "
                f"freed: {seen[:6]}... != {values[:6]}...",
            )
    if not dgraph.check():
        fail(rank, f"[{label}] dgraph.check() failed after heap churn")
    return dgraph


def check_release_drops_retained_arrays(rank, size):
    dgraph = build_from_temporaries(rank, size, as_lists)
    if len([a for a in dgraph._build_arrays if a is not None]) != 6:
        fail(rank, "build() should retain the 6 arrays it was given")
    dgraph.free()
    if dgraph._build_arrays != ():
        fail(rank, "free() must release the retained input arrays")
    dgraph.exit()

    dgraph = build_from_temporaries(rank, size, as_wrong_width)
    dgraph.exit()
    if dgraph._build_arrays != () or dgraph._queue_work is not None:
        fail(rank, "exit() must release the retained input arrays and the work array")


# --------------------------------------------------------------------------
# 2. edgegsttab: an output array filled in place by ghst()
# --------------------------------------------------------------------------


def check_edgegsttab_workflow(rank, size):
    dtype = lib.get_scotch_dtype()
    arrays = local_ring(rank, size)
    n_loc = RING // size
    first = rank * n_loc

    edgegsttab = np.full(len(arrays["edgeloctab"]), -1, dtype=dtype)  # sentinel
    dgraph = Dgraph()
    dgraph.build(
        as_lists(arrays["vertloctab"]),
        as_lists(arrays["edgeloctab"]),
        edgegsttab=edgegsttab,
    )
    if address(dgraph.data(want_edgegsttab=True)["edgegsttab"]) != edgegsttab.ctypes.data:
        fail(
            rank,
            "Scotch does not hold the caller's edgegsttab: ghst() results would go elsewhere",
        )
    if dgraph._build_arrays[BUILD_ARRAYS.index("edgegsttab")] is not edgegsttab:
        fail(rank, "the caller's edgegsttab must be retained as is (no copy)")

    dgraph.ghst()
    vertgstnbr = dgraph.data(want_vertgstnbr=True)["vertgstnbr"]
    if np.any(edgegsttab < 0):
        fail(
            rank,
            f"ghst() left sentinel entries in the caller's edgegsttab: {edgegsttab}",
        )
    if np.any(edgegsttab >= vertgstnbr):
        fail(
            rank,
            f"ghst() wrote ghost indices >= vertgstnbr ({vertgstnbr}): {edgegsttab}",
        )
    for k, g in enumerate(arrays["edgeloctab"]):
        if first <= g < first + n_loc:  # local neighbour -> its local index
            if edgegsttab[k] != g - first:
                fail(
                    rank,
                    f"edgegsttab[{k}] = {edgegsttab[k]}, expected local index {g - first}",
                )
        elif edgegsttab[k] < n_loc:  # remote neighbour -> a ghost index
            fail(
                rank,
                f"edgegsttab[{k}] = {edgegsttab[k]} is not a ghost index for remote vertex {g}",
            )
    if vertgstnbr != n_loc + 2:  # a ring slice has exactly two remote neighbours
        fail(rank, f"expected 2 ghost vertices, vertgstnbr = {vertgstnbr}")
    dgraph.exit()

    # Refusals: anything that would need converting is an error BEFORE any call
    n_edges = len(arrays["edgeloctab"])
    bad_arrays = {
        "wrong width": np.full(n_edges, -1, dtype=wrong_dtype()),
        "python list": [-1] * n_edges,
        "strided view": np.full(2 * n_edges, -1, dtype=dtype)[::2],
    }
    for label, bad in bad_arrays.items():
        dgraph = Dgraph()
        try:
            dgraph.build(
                as_lists(arrays["vertloctab"]),
                as_lists(arrays["edgeloctab"]),
                edgegsttab=bad,
            )
        except TypeError as e:
            if "edgegsttab" not in str(e):
                fail(rank, f"edgegsttab refusal does not name the argument: {e}")
        else:
            fail(
                rank,
                f"build() accepted a {label} edgegsttab; ghst() results would land in a temporary",
            )
        dgraph.exit()


# --------------------------------------------------------------------------
# 3. grow(): the queue work array
# --------------------------------------------------------------------------


def check_grow_work_array(dgraph, rank, size):
    dtype = lib.get_scotch_dtype()
    data = dgraph.data(want_baseval=True, want_vertlocnbr=True)
    baseval, vertlocnbr = data["baseval"], data["vertlocnbr"]
    dgraph.ghst()
    vertgstnbr = dgraph.data(want_vertgstnbr=True)["vertgstnbr"]

    for label, seed_dtype in (("Scotch width", dtype), ("wrong width", wrong_dtype())):
        seedloctab = np.array([baseval], dtype=seed_dtype)  # ONE entry, vertlocnbr needed by C
        seeds_before = seedloctab.copy()
        partgsttab = np.full(vertgstnbr, -1, dtype=dtype)
        partgsttab[0] = rank
        dgraph.grow(1, seedloctab, 3, partgsttab)

        if not np.array_equal(seedloctab, seeds_before) or seedloctab.dtype != seed_dtype:
            fail(
                rank,
                f"[{label}] grow() clobbered the caller's seed array: {seedloctab}",
            )
        # grow is collective: each rank's seed (its first local vertex, global
        # rank*vertlocnbr) spreads 3 steps both ways around the ring, so it
        # reaches its own local vertices 1..3 and, across the rank boundary,
        # the OTHER rank's last three local vertices. Exact expected result:
        expected = np.full(vertlocnbr, -1, dtype=dtype)
        expected[0:4] = rank
        expected[vertlocnbr - 3 :] = (rank + 1) % size
        # (ghost slots partgsttab[vertlocnbr:] are not refreshed by grow: not asserted)
        if not np.array_equal(partgsttab[:vertlocnbr], expected):
            fail(
                rank,
                f"[{label}] grow() partition {partgsttab[:vertlocnbr].tolist()} != expected {expected.tolist()}",
            )

        work = dgraph._queue_work
        if work is None or work.dtype != dtype or len(work) != max(vertlocnbr, 1):
            fail(
                rank,
                f"[{label}] work array must have vertlocnbr={vertlocnbr} entries, got {work!r}",
            )
        if work[0] != baseval:
            fail(rank, f"[{label}] work array does not start with the seeds: {work[:4]}")
        if int((work[1:] != 0).sum()) == 0:
            fail(
                rank,
                f"[{label}] Scotch wrote nothing past the seeds in the work array -- the queue "
                "re-use this array exists for did not happen",
            )

    # partgsttab is an output: anything that would need converting is refused
    seedloctab = np.array([baseval], dtype=dtype)
    bad_arrays = {
        "wrong width": np.full(vertgstnbr, -1, dtype=wrong_dtype()),
        "python list": [-1] * vertgstnbr,
        "strided view": np.full(2 * vertgstnbr, -1, dtype=dtype)[::2],
    }
    for label, bad in bad_arrays.items():
        try:
            dgraph.grow(1, seedloctab, 3, bad)
        except TypeError as e:
            if "partgsttab" not in str(e):
                fail(rank, f"partgsttab refusal does not name the argument: {e}")
        else:
            fail(
                rank,
                f"grow() accepted a {label} partgsttab; results would go to a temporary",
            )

    # Declared seed count must fit the array
    partgsttab = np.full(vertgstnbr, -1, dtype=dtype)
    for count in (2, -1):
        try:
            dgraph.grow(count, seedloctab, 3, partgsttab)
        except ValueError:
            pass
        else:
            fail(rank, f"grow() accepted seedlocnbr={count} for a 1-entry seed array")


# --------------------------------------------------------------------------
# 4. band / redist / induce_part: const inputs of any width or layout
# --------------------------------------------------------------------------


def check_const_inputs(dgraph, rank, size, label, convert):
    data = dgraph.data(want_baseval=True, want_vertlocnbr=True)
    baseval, vertlocnbr = data["baseval"], data["vertlocnbr"]
    first = rank * vertlocnbr

    # band: one-entry frontier (same queue contract as grow)
    fronloctab = convert([baseval])
    fron_before = np.array(fronloctab).copy()
    band = Dgraph()
    dgraph.band(1, fronloctab, 2, band)
    if not band.check():
        fail(rank, f"[{label}] band graph from a converted frontier is invalid")
    if not np.array_equal(np.array(fronloctab), fron_before):
        fail(rank, f"[{label}] band() clobbered the caller's frontier array")
    band_vertglbnbr = band.data(want_vertglbnbr=True)["vertglbnbr"]
    # distance <= 2 around each rank's first vertex: 5 vertices each, no overlap on a 40-ring
    if band_vertglbnbr != 5 * size:
        fail(
            rank,
            f"[{label}] band graph has {band_vertglbnbr} vertices, expected {5 * size}",
        )
    band.exit()

    # redist: swap the two halves
    partloctab = convert([(rank + 1) % size] * vertlocnbr)
    redist = Dgraph()
    dgraph.redist(partloctab, dstgrafdat=redist)
    if not redist.check():
        fail(
            rank,
            f"[{label}] redistributed graph from a converted part array is invalid",
        )
    if redist.data(want_vertlocnbr=True)["vertlocnbr"] != vertlocnbr:
        fail(
            rank,
            f"[{label}] redistributed graph has the wrong number of local vertices",
        )
    redist.exit()

    # induce_part: keep the even global vertices
    keep = [1 if (first + i) % 2 == 0 else 0 for i in range(vertlocnbr)]
    orgpartloctab = convert(keep)
    induced = Dgraph()
    dgraph.induce_part(orgpartloctab, 1, sum(keep), induced)
    if not induced.check():
        fail(rank, f"[{label}] induced graph from a converted part array is invalid")
    if induced.data(want_vertlocnbr=True)["vertlocnbr"] != vertlocnbr // 2:
        fail(rank, f"[{label}] induced graph has the wrong number of vertices")
    induced.exit()


def main():
    try:
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()
        if size != 2:
            if rank == 0:
                print(f"ERROR: this test requires exactly 2 MPI processes, got {size}")
            mpi.finalize()
            return 1

        for label, convert in CONVERSIONS:
            check_build_owns_its_arrays(rank, size, label, convert).exit()
        check_release_drops_retained_arrays(rank, size)
        check_edgegsttab_workflow(rank, size)

        dgraph = build_from_temporaries(rank, size, as_lists)
        check_grow_work_array(dgraph, rank, size)
        for label, convert in CONVERSIONS[1:]:  # wrong width, strided view
            check_const_inputs(dgraph, rank, size, label, convert)
        dgraph.exit()

        mpi.finalize()
        if rank == 0:
            print("PASS: Dgraph owns every array it hands to Scotch, for any width or layout")
        os._exit(0)
    except Exception as e:  # noqa: BLE001 -- any failure must reach stdout and exit non-zero
        rank = mpi.comm_rank() if mpi.is_initialized() else "?"
        print(f"ERROR on rank {rank}: {e}")
        import traceback

        traceback.print_exc()
        if mpi.is_initialized():
            mpi.finalize()
        os._exit(1)


if __name__ == "__main__":
    sys.exit(main())
