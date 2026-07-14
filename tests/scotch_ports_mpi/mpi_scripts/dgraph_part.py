#!/usr/bin/env python3
"""
Test for SCOTCH_dgraphPart() / SCOTCH_dgraphMap() / SCOTCH_dgraphMapView().

Partitions a distributed graph and validates that every vertex receives a
valid part and that no part is empty. There is no upstream C test for
SCOTCH_dgraphPart; this test mirrors the structure of the dgraph_band.py
port (per-rank output aggregated through a shared file with barriers).

Run with: mpirun -np 3 python dgraph_part.py <graph_file> <output_file>
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
from pyscotch.arch import Architecture

NPARTS = 4


def main():
    """Test distributed graph partitioning."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()
        size = mpi.comm_size()

        # Check arguments
        if len(sys.argv) != 3:
            if rank == 0:
                print(f"usage: {sys.argv[0]} graph_file output_file")
            mpi.finalize()
            return 1

        graph_file = Path(sys.argv[1])
        output_file = Path(sys.argv[2])

        if not graph_file.exists():
            if rank == 0:
                print(f"ERROR: Graph file not found: {graph_file}")
            mpi.finalize()
            return 1

        lib.SCOTCH_randomReset()

        # Barrier: Synchronize for debug
        mpi.barrier()

        # Initialize and load source graph
        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        mpi.barrier()

        data = grafdat.data(want_vertglbnbr=True, want_vertlocnbr=True)
        vertglbnbr = data["vertglbnbr"]
        vertlocnbr = data["vertlocnbr"]

        # --- SCOTCH_dgraphPart ---
        partloctab = grafdat.part(NPARTS)

        assert len(partloctab) == vertlocnbr, "partloctab has wrong length"
        assert np.all(partloctab >= 0) and np.all(partloctab < NPARTS), (
            f"invalid part values on rank {rank}: "
            f"min={partloctab.min()}, max={partloctab.max()}"
        )

        # --- SCOTCH_dgraphMap onto a complete architecture: same contract ---
        archdat = Architecture()
        archdat.complete(NPARTS)
        maploctab = grafdat.map(archdat)
        assert len(maploctab) == vertlocnbr, "maploctab has wrong length"
        assert np.all(maploctab >= 0) and np.all(
            maploctab < NPARTS
        ), f"invalid mapping values on rank {rank}"

        # --- 3-step SCOTCH_dgraphMapInit/MapCompute/MapExit API ---
        maploctab2 = grafdat.map_compute(archdat)
        assert len(maploctab2) == vertlocnbr, "map_compute result has wrong length"
        assert np.all(maploctab2 >= 0) and np.all(
            maploctab2 < NPARTS
        ), f"invalid map_compute values on rank {rank}"

        # --- SCOTCH_dgraphMapView: mapping statistics written on root ---
        view_file = output_file.with_suffix(".view")
        grafdat.map_view(view_file, archdat)
        if rank == 0:
            assert (
                view_file.exists() and view_file.stat().st_size > 0
            ), "map_view produced no output"

        # Aggregate part values through a shared file (barrier-sequenced),
        # then validate globally on rank 0.
        for procnum in range(size):
            mpi.barrier()
            if procnum == rank:
                mode = "w" if procnum == 0 else "a"
                with open(output_file, mode) as f:
                    for part in partloctab:
                        f.write(f"{part}\n")
        mpi.barrier()

        if rank == 0:
            parts = np.loadtxt(output_file, dtype=np.int64, ndmin=1)
            assert len(parts) == vertglbnbr, f"expected {vertglbnbr} part values, got {len(parts)}"
            assert np.all(parts >= 0) and np.all(parts < NPARTS), "invalid global part values"
            counts = np.bincount(parts, minlength=NPARTS)
            assert np.all(counts > 0), f"empty part(s): counts={counts.tolist()}"

        # Clean up
        archdat.close()
        grafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Part test completed successfully")
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
