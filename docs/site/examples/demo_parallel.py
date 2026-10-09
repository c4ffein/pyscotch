"""Act 3 — PT-Scotch: each rank holds a slice of the graph.

    PYSCOTCH_PARALLEL=1 mpirun -n 2 python demo_parallel.py

Also works WITHOUT mpirun (MPI singleton init -> a valid 1-rank job): the
whole Dgraph API under a plain debugger during development.
"""

import os
from collections import Counter

os.environ.setdefault("PYSCOTCH_PARALLEL", "1")

from mpi4py import MPI

from pyscotch import Dgraph, scotch_version

comm = MPI.COMM_WORLD
dg = Dgraph(comm=comm)          # any communicator works, not just COMM_WORLD
dg.build_grid_3d(16, 16, 16)    # 4096 vertices, sliced across the ranks
assert dg.check()
part = dg.part(4)               # collective: local assignments on each rank
sizes = comm.allreduce(Counter(part.tolist()))
dg.exit()

if comm.Get_rank() == 0:
    version = ".".join(map(str, scotch_version()))
    print(f"PT-Scotch {version} across {comm.Get_size()} rank(s)")
    print(f"global part sizes: {dict(sorted(sizes.items()))}")
