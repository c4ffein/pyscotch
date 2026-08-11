#!/usr/bin/env python3
"""PyScotch counterpart of `dgord` for the parallel differential tier.

Run under mpirun; mirrors dgord's call sequence exactly (SCOTCH_randomProc with
the process rank, SCOTCH_dgraphLoad with baseval=-1, SCOTCH_dgraphOrderInit/
Compute, and a root-process SCOTCH_dgraphOrderSave). The resulting centralized
ordering file must be byte-identical to dgord's under deterministic settings.

The per-rank ``random_proc(rank)`` is essential and non-obvious: the CLI tools
seed the generator with the process number (dgord.c:159), and that per-rank
divergence is what drives the distributed candidate election (see the fold-dup
note in QUESTIONS_FOR_SCOTCH_TEAM.md). Without it, all ranks share one seed and
non-trivial graphs (weighted, or large enough to really coarsen across ranks)
produce a different — still valid — ordering, breaking byte-identity.

Usage: mpirun -np N python differential_dgord.py <graph.grf> <out.ord>
The parallel variant is selected via the environment the launcher sets
(PYSCOTCH_INT_SIZE, PYSCOTCH_PARALLEL=1, PYSCOTCH_LIB_DIR).
"""
import sys
from pathlib import Path

from pyscotch import random_proc
from pyscotch.dgraph import Dgraph
from pyscotch.mpi import mpi


def main():
    graph_file, out_file = sys.argv[1], sys.argv[2]

    mpi.init()
    try:
        random_proc(mpi.comm_rank())  # like dgord.c:159: SCOTCH_randomProc(proclocnum)
        dg = Dgraph()
        dg.load(Path(graph_file), baseval=-1)  # like dgord: preserve file base
        dordering = dg.order_init()
        dg.order_compute(dordering)  # default strategy, like dgord with no -o
        dg.order_save(dordering, out_file)  # root writes the centralized ordering
        dg.order_exit(dordering)
    finally:
        mpi.finalize()


if __name__ == "__main__":
    main()
