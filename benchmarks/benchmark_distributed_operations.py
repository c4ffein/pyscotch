#!/usr/bin/env python3
"""
Benchmark: Distributed Graph Operations

Benchmarks PyScotch distributed operations with MPI.

Usage:
    mpirun -np <num_procs> python benchmark_distributed_operations.py <graph_file>

Example:
    mpirun -np 4 python benchmark_distributed_operations.py ../external/scotch/src/check/data/bump.grf
"""

import sys
import time
from pathlib import Path

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscotch import libscotch as lib
from pyscotch.mpi import mpi
from pyscotch.dgraph import Dgraph, COARSEN_NONE


def benchmark_load(graph_file: Path, iterations: int = 5):
    """Benchmark distributed graph loading."""

    times = []

    for i in range(iterations):
        grafdat = Dgraph()

        start = time.perf_counter()
        grafdat.load(graph_file, baseval=-1, flagval=0)
        end = time.perf_counter()

        times.append(end - start)

        if i == 0:
            data = grafdat.data(
                want_vertglbnbr=True,
                want_vertlocnbr=True,
                want_edgeglbnbr=True
            )
            first_result = data

        grafdat.exit()

    return {
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'times': times,
        'data': first_result
    }


def benchmark_check(graph_file: Path, iterations: int = 5):
    """Benchmark distributed graph validation."""

    grafdat = Dgraph()
    grafdat.load(graph_file, baseval=-1, flagval=0)

    times = []

    for i in range(iterations):
        start = time.perf_counter()
        result = grafdat.check()
        end = time.perf_counter()

        times.append(end - start)

    grafdat.exit()

    return {
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'times': times
    }


def benchmark_coarsen(graph_file: Path, iterations: int = 3):
    """Benchmark distributed graph coarsening."""

    times = []
    success_count = 0

    for i in range(iterations):
        grafdat = Dgraph()
        grafdat.load(graph_file, baseval=-1, flagval=0)

        start = time.perf_counter()
        coargrafdat, multloctab = grafdat.coarsen(coarrat=0.8, foldval=COARSEN_NONE)
        end = time.perf_counter()

        times.append(end - start)

        if multloctab is not None:
            success_count += 1
            if i == 0:
                coar_data = coargrafdat.data(want_vertglbnbr=True)
                orig_data = grafdat.data(want_vertglbnbr=True)
                ratio = float(coar_data['vertglbnbr']) / float(orig_data['vertglbnbr'])
                first_ratio = ratio

            coargrafdat.exit()

        grafdat.exit()

    result = {
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'times': times,
        'success_count': success_count
    }

    if success_count > 0:
        result['ratio'] = first_ratio

    return result


def benchmark_ghst(graph_file: Path, iterations: int = 5):
    """Benchmark ghost edge computation."""

    grafdat = Dgraph()
    grafdat.load(graph_file, baseval=-1, flagval=0)

    times = []

    for i in range(iterations):
        start = time.perf_counter()
        grafdat.ghst()
        end = time.perf_counter()

        times.append(end - start)

    grafdat.exit()

    return {
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'times': times
    }


def main():
    if len(sys.argv) < 2:
        print(f"Usage: mpirun -np <N> {sys.argv[0]} <graph_file> [iterations]")
        print(f"\nExample:")
        print(f"  mpirun -np 4 {sys.argv[0]} ../external/scotch/src/check/data/bump.grf 10")
        return 1

    graph_file = Path(sys.argv[1])
    if not graph_file.exists():
        print(f"ERROR: Graph file not found: {graph_file}")
        return 1

    iterations = 5
    if len(sys.argv) >= 3:
        try:
            iterations = int(sys.argv[2])
        except ValueError:
            print("ERROR: iterations must be an integer")
            return 1

    # Initialize MPI
    mpi.init()
    rank = mpi.comm_rank()
    size = mpi.comm_size()

    lib.set_active_variant(64, parallel=True)

    if rank == 0:
        print("=" * 70)
        print("Distributed Graph Operations Benchmark")
        print("=" * 70)
        print(f"Graph file: {graph_file}")
        print(f"Processes:  {size}")
        print(f"Iterations: {iterations}")
        print()

    # Benchmark load
    if rank == 0:
        print("[1/4] Benchmarking graph loading...")

    load_results = benchmark_load(graph_file, iterations)

    if rank == 0:
        print(f"  Graph: {load_results['data']['vertglbnbr']} vertices (global)")
        print(f"  Rank 0: {load_results['data']['vertlocnbr']} vertices (local)")
        print(f"  Average time: {load_results['avg_time']*1000:.2f} ms")
        print(f"  Min time:     {load_results['min_time']*1000:.2f} ms")
        print(f"  Max time:     {load_results['max_time']*1000:.2f} ms")
        print()

    # Benchmark check
    if rank == 0:
        print("[2/4] Benchmarking graph validation...")

    check_results = benchmark_check(graph_file, iterations)

    if rank == 0:
        print(f"  Average time: {check_results['avg_time']*1000:.2f} ms")
        print(f"  Min time:     {check_results['min_time']*1000:.2f} ms")
        print(f"  Max time:     {check_results['max_time']*1000:.2f} ms")
        print()

    # Benchmark coarsen
    if rank == 0:
        print("[3/4] Benchmarking graph coarsening...")

    coarsen_results = benchmark_coarsen(graph_file, min(3, iterations))

    if rank == 0:
        print(f"  Average time: {coarsen_results['avg_time']*1000:.2f} ms")
        print(f"  Min time:     {coarsen_results['min_time']*1000:.2f} ms")
        print(f"  Max time:     {coarsen_results['max_time']*1000:.2f} ms")
        if 'ratio' in coarsen_results:
            print(f"  Coarsening ratio: {coarsen_results['ratio']:.4f}")
        print()

    # Benchmark ghst
    if rank == 0:
        print("[4/4] Benchmarking ghost edge computation...")

    ghst_results = benchmark_ghst(graph_file, iterations)

    if rank == 0:
        print(f"  Average time: {ghst_results['avg_time']*1000:.2f} ms")
        print(f"  Min time:     {ghst_results['min_time']*1000:.2f} ms")
        print(f"  Max time:     {ghst_results['max_time']*1000:.2f} ms")
        print()

    # Summary
    if rank == 0:
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Graph size: {load_results['data']['vertglbnbr']} vertices, "
              f"{load_results['data']['edgeglbnbr']} edges")
        print(f"Processes:  {size}")
        print()
        print("Operation           Avg Time    Min Time    Max Time")
        print("-" * 70)
        print(f"Load               {load_results['avg_time']*1000:8.2f} ms  "
              f"{load_results['min_time']*1000:8.2f} ms  "
              f"{load_results['max_time']*1000:8.2f} ms")
        print(f"Check              {check_results['avg_time']*1000:8.2f} ms  "
              f"{check_results['min_time']*1000:8.2f} ms  "
              f"{check_results['max_time']*1000:8.2f} ms")
        print(f"Coarsen            {coarsen_results['avg_time']*1000:8.2f} ms  "
              f"{coarsen_results['min_time']*1000:8.2f} ms  "
              f"{coarsen_results['max_time']*1000:8.2f} ms")
        print(f"Ghost (ghst)       {ghst_results['avg_time']*1000:8.2f} ms  "
              f"{ghst_results['min_time']*1000:8.2f} ms  "
              f"{ghst_results['max_time']*1000:8.2f} ms")
        print()
        print("=" * 70)

    mpi.finalize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
