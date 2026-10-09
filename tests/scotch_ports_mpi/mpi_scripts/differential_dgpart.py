#!/usr/bin/env python3
"""PyScotch counterpart of `dgpart` for the parallel differential tier.

Run under mpirun; mirrors dgpart's call sequence exactly (SCOTCH_randomProc
with the process rank, SCOTCH_dgraphLoad with baseval=-1, a complete-graph
target architecture, SCOTCH_dgraphMapCompute, and a root-process
SCOTCH_dgraphMapSave). The resulting centralized mapping file must be
byte-identical to dgpart's under deterministic settings.

The per-rank ``random_proc(rank)`` is essential and non-obvious: the CLI tools
seed the generator with the process number (dgmap.c:181), and that per-rank
divergence is what drives the distributed fold-dup candidate election (see the
fold-dup note in QUESTIONS_FOR_SCOTCH_TEAM.md). Without it, all ranks share one
seed and non-trivial graphs (weighted, or large enough to really coarsen across
ranks) elect a different — still valid — result, breaking byte-identity.

Usage: mpirun -np N python differential_dgpart.py <graph.grf> <out.map> <nparts>
The parallel variant is selected via the environment the launcher sets
(PYSCOTCH_INT_SIZE, PYSCOTCH_PARALLEL=1, PYSCOTCH_LIB_DIR).
"""

import sys
from pathlib import Path

from pyscotch import random_proc
from pyscotch.arch import Architecture
from pyscotch.dgraph import Dgraph
from pyscotch.mpi import mpi


def main():
    graph_file, out_file, nparts = sys.argv[1], sys.argv[2], int(sys.argv[3])

    mpi.init()
    try:
        random_proc(mpi.comm_rank())  # like dgmap.c:181: SCOTCH_randomProc(proclocnum)
        dg = Dgraph()
        dg.load(Path(graph_file), baseval=-1)  # like dgpart: preserve file base
        arch = Architecture()
        arch.complete(nparts)  # dgpart maps onto a complete graph of nparts
        dg.map_save(out_file, arch)  # root writes the centralized mapping
    finally:
        mpi.finalize()


if __name__ == "__main__":
    main()
