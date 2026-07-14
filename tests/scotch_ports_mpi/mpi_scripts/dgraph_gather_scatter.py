#!/usr/bin/env python3
"""
Test for SCOTCH_dgraphScatter() / SCOTCH_dgraphGather().

Roundtrip: the root process loads a centralized (sequential) graph, scatters
it into a distributed graph, then gathers it back into a new centralized
graph and checks that the adjacency structure is identical. There is no
upstream C test for these routines; the test mirrors the structure of the
other dgraph_*.py ports.

Run with: mpirun -np 3 python dgraph_gather_scatter.py <graph_file>
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
from pyscotch.graph import Graph


def sorted_adjacency(graph):
    """Return (indptr, per-vertex sorted neighbor arrays) for comparison."""
    indptr, indices, _ = graph._csr_arrays()
    neighbors = [
        np.sort(indices[int(indptr[i]) : int(indptr[i + 1])]) for i in range(len(indptr) - 1)
    ]
    return indptr, neighbors


def main():
    """Test centralized <-> distributed graph conversion roundtrip."""
    try:
        # Initialize MPI
        mpi.init()
        rank = mpi.comm_rank()

        # Check arguments
        if len(sys.argv) != 2:
            if rank == 0:
                print(f"usage: {sys.argv[0]} graph_file")
            mpi.finalize()
            return 1

        graph_file = Path(sys.argv[1])
        if not graph_file.exists():
            if rank == 0:
                print(f"ERROR: Graph file not found: {graph_file}")
            mpi.finalize()
            return 1

        # Barrier: Synchronize for debug
        mpi.barrier()

        # Root process loads the centralized graph; others pass None
        cgrfdat = None
        if rank == 0:
            cgrfdat = Graph()
            cgrfdat.load(graph_file)
            vertnbr, edgenbr = cgrfdat.size()

        # Scatter centralized graph into the distributed graph
        grafdat = Dgraph()
        grafdat.scatter(cgrfdat)

        assert grafdat.check(), "scattered graph is inconsistent"

        data = grafdat.data(want_vertglbnbr=True, want_edgeglbnbr=True)
        if rank == 0:
            assert data["vertglbnbr"] == vertnbr, (
                f"vertex count mismatch after scatter: " f"{data['vertglbnbr']} != {vertnbr}"
            )
            assert (
                data["edgeglbnbr"] == edgenbr
            ), f"edge count mismatch after scatter: {data['edgeglbnbr']} != {edgenbr}"

        # Gather back into a new centralized graph on the root process
        gathered = Graph() if rank == 0 else None
        grafdat.gather(gathered)

        if rank == 0:
            assert gathered.check(), "gathered graph is inconsistent"
            assert gathered.size() == (
                vertnbr,
                edgenbr,
            ), f"size mismatch after gather: {gathered.size()} != {(vertnbr, edgenbr)}"
            # Full adjacency roundtrip check (neighbor order may differ)
            orig_indptr, orig_neighbors = sorted_adjacency(cgrfdat)
            gath_indptr, gath_neighbors = sorted_adjacency(gathered)
            assert np.array_equal(orig_indptr, gath_indptr), "indptr mismatch after roundtrip"
            for vertnum, (orig, gath) in enumerate(zip(orig_neighbors, gath_neighbors)):
                assert np.array_equal(
                    orig, gath
                ), f"adjacency mismatch for vertex {vertnum} after roundtrip"
            gathered.close()
            cgrfdat.close()

        # Clean up
        grafdat.exit()
        mpi.finalize()

        if rank == 0:
            print("\nPASS: Gather/scatter roundtrip test completed successfully")
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
