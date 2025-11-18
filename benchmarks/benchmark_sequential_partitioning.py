#!/usr/bin/env python3
"""
Benchmark: Sequential Graph Partitioning

Compares PyScotch performance against native Scotch for graph partitioning.

Usage:
    python benchmark_sequential_partitioning.py <graph_file> <num_parts>

Example:
    python benchmark_sequential_partitioning.py ../external/scotch/src/check/data/bump.grf 4
"""

import sys
import time
from pathlib import Path
import subprocess
import tempfile

# Add pyscotch to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscotch import Graph, Architecture, Strategies


def benchmark_pyscotch(graph_file: Path, num_parts: int, iterations: int = 5):
    """Benchmark PyScotch partitioning performance."""

    times = []

    for i in range(iterations):
        graph = Graph()
        graph.load(graph_file)

        arch = Architecture.complete_graph(num_parts)
        strategy = Strategies.partition_quality()

        start = time.perf_counter()
        mapping = graph.partition(arch, strategy)
        end = time.perf_counter()

        times.append(end - start)

        # Get partition for validation
        if i == 0:
            parttab = mapping.get_partition_array()
            vertnbr, edgenbr = graph.size()

        graph.exit()

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    return {
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'times': times,
        'vertnbr': vertnbr,
        'edgenbr': edgenbr,
        'parttab': parttab
    }


def benchmark_native_scotch(graph_file: Path, num_parts: int, iterations: int = 5):
    """Benchmark native Scotch gpart performance (if available)."""

    # Check if gpart is available
    try:
        result = subprocess.run(['which', 'gpart'], capture_output=True, text=True)
        if result.returncode != 0:
            return None
    except Exception:
        return None

    times = []

    for i in range(iterations):
        with tempfile.NamedTemporaryFile(suffix=".map", delete=True) as f:
            mapping_file = f.name

            start = time.perf_counter()
            result = subprocess.run(
                ['gpart', str(num_parts), str(graph_file), mapping_file],
                capture_output=True,
                text=True
            )
            end = time.perf_counter()

            if result.returncode != 0:
                print(f"WARNING: gpart failed: {result.stderr}")
                return None

            times.append(end - start)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    return {
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'times': times
    }


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <graph_file> <num_parts> [iterations]")
        print(f"\nExample:")
        print(f"  {sys.argv[0]} ../external/scotch/src/check/data/bump.grf 4 10")
        return 1

    graph_file = Path(sys.argv[1])
    if not graph_file.exists():
        print(f"ERROR: Graph file not found: {graph_file}")
        return 1

    try:
        num_parts = int(sys.argv[2])
        if num_parts < 2:
            print("ERROR: num_parts must be >= 2")
            return 1
    except ValueError:
        print("ERROR: num_parts must be an integer")
        return 1

    iterations = 5
    if len(sys.argv) >= 4:
        try:
            iterations = int(sys.argv[3])
        except ValueError:
            print("ERROR: iterations must be an integer")
            return 1

    print(f"=" * 70)
    print(f"Sequential Graph Partitioning Benchmark")
    print(f"=" * 70)
    print(f"Graph file: {graph_file}")
    print(f"Partitions: {num_parts}")
    print(f"Iterations: {iterations}")
    print()

    # Benchmark PyScotch
    print("Benchmarking PyScotch...")
    pyscotch_results = benchmark_pyscotch(graph_file, num_parts, iterations)

    print(f"  Graph: {pyscotch_results['vertnbr']} vertices, {pyscotch_results['edgenbr']} edges")
    print(f"  Average time: {pyscotch_results['avg_time']*1000:.2f} ms")
    print(f"  Min time:     {pyscotch_results['min_time']*1000:.2f} ms")
    print(f"  Max time:     {pyscotch_results['max_time']*1000:.2f} ms")
    print()

    # Benchmark native Scotch if available
    print("Benchmarking native Scotch (gpart)...")
    native_results = benchmark_native_scotch(graph_file, num_parts, iterations)

    if native_results:
        print(f"  Average time: {native_results['avg_time']*1000:.2f} ms")
        print(f"  Min time:     {native_results['min_time']*1000:.2f} ms")
        print(f"  Max time:     {native_results['max_time']*1000:.2f} ms")
        print()

        # Calculate overhead
        overhead = (pyscotch_results['avg_time'] / native_results['avg_time'] - 1) * 100
        print(f"PyScotch overhead: {overhead:+.1f}%")

        if overhead < 10:
            print("✓ Excellent! PyScotch performance is comparable to native Scotch")
        elif overhead < 25:
            print("✓ Good! PyScotch has acceptable overhead")
        elif overhead < 50:
            print("⚠ Moderate overhead - consider optimizations")
        else:
            print("⚠ High overhead - Python wrapper may be bottleneck")
    else:
        print("  Native gpart not available (skipped)")
        print("  Install Scotch binaries to compare: apt-get install scotch")

    print()

    # Partition quality analysis
    import numpy as np
    parttab = pyscotch_results['parttab']
    part_sizes = np.bincount(parttab, minlength=num_parts)

    print("Partition Quality:")
    print(f"  Partition sizes: {part_sizes}")
    avg_size = len(parttab) / num_parts
    max_size = part_sizes.max()
    imbalance = (max_size - avg_size) / avg_size * 100
    print(f"  Imbalance: {imbalance:.2f}%")

    if imbalance < 5:
        print("  ✓ Excellent balance")
    elif imbalance < 10:
        print("  ✓ Good balance")
    elif imbalance < 20:
        print("  ⚠ Moderate imbalance")
    else:
        print("  ⚠ Poor balance")

    print()
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
