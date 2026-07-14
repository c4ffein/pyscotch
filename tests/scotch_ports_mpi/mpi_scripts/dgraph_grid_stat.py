#!/usr/bin/env python3
"""
Test for SCOTCH_dgraphBuildGrid3D() / SCOTCH_dgraphStat() / SCOTCH_dgraphFree().

Builds a distributed 5x5x5 grid graph without any input file, validates its
statistics, partitions it, frees it and rebuilds a smaller grid to check
that free() leaves the structure reusable. There is no upstream C test for
these routines; the test mirrors the structure of the other dgraph_*.py
ports.

Run with: mpirun -np 2 python dgraph_grid_stat.py
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph


def main():
    """Test 3D grid building, statistics and freeing."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()

        lib.SCOTCH_randomReset()

        # Barrier: Synchronize for debug
        mpi.barrier()

        # Build a distributed 5x5x5 grid (6-neighbor, no wraparound)
        grafdat = Dgraph()
        grafdat.build_grid_3d(5, 5, 5)

        assert grafdat.check(), "grid graph is inconsistent"

        data = grafdat.data(want_vertglbnbr=True, want_vertlocnbr=True)
        assert data["vertglbnbr"] == 125, f"expected 125 vertices, got {data['vertglbnbr']}"

        # Statistics of an unweighted 5x5x5 grid: unit vertex loads, corner
        # vertices have degree 3, interior vertices have degree 6.
        statdat = grafdat.stat()
        assert statdat["velomin"] == 1 and statdat["velomax"] == 1, "unexpected vertex loads"
        assert statdat["velosum"] == 125, f"expected velosum 125, got {statdat['velosum']}"
        assert statdat["degrmin"] == 3, f"expected degrmin 3, got {statdat['degrmin']}"
        assert statdat["degrmax"] == 6, f"expected degrmax 6, got {statdat['degrmax']}"

        # The grid can be partitioned like any other distributed graph
        partloctab = grafdat.part(2)
        assert len(partloctab) == data["vertlocnbr"], "partloctab has wrong length"
        assert np.all(partloctab >= 0) and np.all(partloctab < 2), "invalid part values"

        # free() releases the contents but keeps the structure usable
        grafdat.free()
        grafdat.build_grid_3d(4, 4, 4, flagval=lib.SCOTCH_DGRAPHBUILDGRID3DTORUS)
        assert grafdat.check(), "rebuilt torus graph is inconsistent"
        data = grafdat.data(want_vertglbnbr=True)
        assert data["vertglbnbr"] == 64, f"expected 64 vertices, got {data['vertglbnbr']}"
        # In a 4x4x4 torus every vertex has exactly 6 neighbors
        statdat = grafdat.stat()
        assert statdat["degrmin"] == 6 and statdat["degrmax"] == 6, "unexpected torus degrees"

        # Clean up
        grafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Grid/stat test completed successfully")
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
