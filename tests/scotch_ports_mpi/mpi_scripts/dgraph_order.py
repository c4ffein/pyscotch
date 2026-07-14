#!/usr/bin/env python3
"""
Port of test_scotch_dgraph_order.c

Tests the SCOTCH_dgraphOrderCompute() and SCOTCH_dgraphOrderComputeList()
routines.

Reference: external/scotch/src/check/test_scotch_dgraph_order.c

Run with: mpirun -np 3 python dgraph_order.py <graph_file>
"""

import ctypes
import sys
import os
from ctypes import byref, c_int, c_void_p
from pathlib import Path
import numpy as np

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph
from pyscotch.strategy import Strategy


def mpi_reduce_sum_num(value: int) -> int:
    """MPI_Reduce(MPI_SUM) of one SCOTCH_Num to rank 0 (C code: line 323).

    pyscotch.mpi does not wrap MPI_Reduce, so bind it here, resolving the
    predefined datatype/op handles like mpi.py resolves MPI_COMM_WORLD
    (OpenMPI globals first, MPICH integer constants as fallback).
    """
    libmpi = mpi._libmpi
    bits = lib.get_scotch_int_size()
    try:  # OpenMPI: handles are addresses of global objects
        dtype_sym = "ompi_mpi_int64_t" if bits == 64 else "ompi_mpi_int32_t"
        datatype = ctypes.addressof(ctypes.c_void_p.in_dll(libmpi, dtype_sym))
        op_sum = ctypes.addressof(ctypes.c_void_p.in_dll(libmpi, "ompi_mpi_op_sum"))
    except ValueError:  # MPICH: handles are integer constants
        datatype = 0x4C00083A if bits == 64 else 0x4C000439  # MPI_INT64_T / MPI_INT32_T
        op_sum = 0x58000003  # MPI_SUM
    libmpi.MPI_Reduce.restype = c_int
    libmpi.MPI_Reduce.argtypes = [c_void_p, c_void_p, c_int, c_void_p, c_void_p, c_int, c_void_p]
    sendval = lib.SCOTCH_Num(value)
    recvval = lib.SCOTCH_Num(0)
    if libmpi.MPI_Reduce(
        byref(sendval),
        byref(recvval),
        1,
        c_void_p(datatype),
        c_void_p(op_sum),
        0,
        mpi.get_comm_world(),
    ):
        print("main: cannot communicate (2)")
        os._exit(1)
    return recvval.value


def list_fill_random(listlocnbr, listloctab, baseval, vertlocnbr):
    """Fill a list array with a subset of based vertex indices.

    C code: listFillRandom(), lines 76-103.
    Returns 0 if the list array could be filled, !0 on error.
    """
    if listlocnbr > vertlocnbr:
        print("listFillRandom: invalid arguments")
        return 1

    if listlocnbr == 0:  # If nothing to do
        return 0

    vertlocnum = baseval  # If list is full, take all vertices
    if listlocnbr < vertlocnbr:  # Else select only a vertex range
        vertlocnum += lib.SCOTCH_randomVal(vertlocnbr - listlocnbr + 1)

    for listlocidx in range(listlocnbr):
        listloctab[listlocidx] = vertlocnum
        vertlocnum += 1

    return 0


def perm_gather(grafdat, dordering, permtab, proclocnum):
    """Gather ordering results on root process.

    C code: permGather(), lines 111-142.
    Returns 0 on success, !0 on error.
    """
    cordering = None
    if proclocnum == 0:
        try:
            cordering = grafdat.corder_init(permtab=permtab)
        except RuntimeError as e:
            print(f"permGather: cannot initialize distributed ordering: {e}")
            return 1

    try:
        grafdat.order_gather(dordering, cordering)
    except RuntimeError as e:
        print(f"permGather: cannot gather distributed ordering: {e}")
        return 1

    if cordering is not None:
        grafdat.corder_exit(cordering)

    return 0


def perm_check_identity(permtab, baseval, vertnbr):
    """C code: permCheckIdentity(), lines 144-159."""
    for vertnum in range(vertnbr):
        if permtab[vertnum] != vertnum + baseval:
            return 1
    return 0


def perm_check_list(permtab, baseval, listlocnbr, listloctab, listglbnbr):
    """C code: permCheckList(), lines 161-180."""
    for listlocidx in range(listlocnbr):  # For all vertices in list
        if permtab[listloctab[listlocidx] - baseval] >= listglbnbr + baseval:
            return 1  # Must be ordered first
    return 0


def main():
    """Test distributed graph ordering (port of test_scotch_dgraph_order.c)."""
    try:
        # Initialize MPI
        mpi.init()
        proclocnum = mpi.comm_rank()
        procglbnbr = mpi.comm_size()

        # Check arguments
        if len(sys.argv) != 2:
            if proclocnum == 0:
                print(f"usage: {sys.argv[0]} graph_file")
            mpi.finalize()
            return 1

        graph_file = Path(sys.argv[1])
        if not graph_file.exists():
            if proclocnum == 0:
                print(f"ERROR: Graph file not found: {graph_file}")
            mpi.finalize()
            return 1

        # C code: line 242
        lib.SCOTCH_randomReset()

        # Barrier: Synchronize for debug (C code: line 244)
        mpi.barrier()

        # Initialize and load graph (C code: lines 252-262)
        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        # C code: lines 264-265
        data = grafdat.data(want_baseval=True, want_vertglbnbr=True, want_vertlocnbr=True)
        baseval = data["baseval"]
        vertglbnbr = data["vertglbnbr"]
        vertlocnbr = data["vertlocnbr"]

        # C code: line 267 - permtab of size vertglbnbr
        permtab = np.zeros(vertglbnbr, dtype=lib.get_scotch_dtype())

        # C code: lines 272-276
        stradat = Strategy()
        stradat.build_dgraph_ordering(0, procglbnbr, 0, 0.2)

        # --- First ordering: empty lists on all ranks => identity ---
        # C code: lines 278-286
        dorddat = grafdat.order_init()
        grafdat.order_compute_list(dorddat, None, stradat, reset_random=False)

        # C code: lines 288-297
        permtab.fill(-1)
        if perm_gather(grafdat, dorddat, permtab, proclocnum) != 0:
            print("main: error checking ordering (1)")
            os._exit(1)
        if proclocnum == 0 and perm_check_identity(permtab, baseval, vertglbnbr) != 0:
            print("main: invalid ordering (1)")
            os._exit(1)

        # C code: line 299
        grafdat.order_exit(dorddat)

        # --- Second ordering: mixed full/partial/empty local lists ---
        # C code: lines 301-316
        dorddat = grafdat.order_init()

        if proclocnum == 0:
            listlocnbr = vertlocnbr  # Experiment with a full local list
        elif proclocnum == (procglbnbr - 1):
            listlocnbr = 0  # And an empty local list
        else:
            listlocnbr = (9 * vertlocnbr) // 10  # And a partial local list
        listloctab = np.zeros(listlocnbr, dtype=lib.get_scotch_dtype())
        list_fill_random(listlocnbr, listloctab, baseval, vertlocnbr)

        # C code: lines 318-321
        grafdat.order_compute_list(dorddat, listloctab, stradat, reset_random=False)

        # C code: lines 323-326
        listglbnbr = mpi_reduce_sum_num(listlocnbr)

        # C code: lines 328-337
        permtab.fill(-1)
        if perm_gather(grafdat, dorddat, permtab, proclocnum) != 0:
            print("main: error checking ordering (2)")
            os._exit(1)
        if (
            proclocnum == 0
            and perm_check_list(permtab, baseval, listlocnbr, listloctab, listglbnbr) != 0
        ):
            print("main: invalid ordering (2)")
            os._exit(1)

        # C code: line 339
        grafdat.order_exit(dorddat)

        # Barrier: Synchronize for debug (C code: line 343)
        mpi.barrier()

        # Clean up (C code: lines 348-349)
        stradat.close()
        grafdat.exit()

        mpi.finalize()

        if proclocnum == 0:
            print("\nPASS: Order test completed successfully")
        os._exit(0)

    except Exception as e:
        rank = mpi.comm_rank() if mpi.is_initialized() else "?"
        print(f"ERROR on rank {rank}: {e}")
        import traceback

        traceback.print_exc()
        if mpi.is_initialized():
            mpi.finalize()
        os._exit(1)


if __name__ == "__main__":
    main()
