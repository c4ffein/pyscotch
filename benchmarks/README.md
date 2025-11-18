# PyScotch Benchmarks

Performance benchmarks for PyScotch operations.

## Available Benchmarks

### 1. Sequential Partitioning
**File:** `benchmark_sequential_partitioning.py`

Compares PyScotch against native Scotch (gpart) for graph partitioning.

**Usage:**
```bash
python benchmark_sequential_partitioning.py <graph_file> <num_parts> [iterations]
```

**Example:**
```bash
python benchmark_sequential_partitioning.py ../external/scotch/src/check/data/bump.grf 4 10
```

**Metrics:**
- Partitioning time (avg, min, max)
- Partition quality (balance, imbalance%)
- Overhead vs native Scotch (if available)

---

### 2. Distributed Operations
**File:** `benchmark_distributed_operations.py`

Benchmarks distributed graph operations with MPI.

**Usage:**
```bash
mpirun -np <N> python benchmark_distributed_operations.py <graph_file> [iterations]
```

**Example:**
```bash
mpirun -np 4 python benchmark_distributed_operations.py ../external/scotch/src/check/data/bump.grf 10
```

**Operations Benchmarked:**
- Graph loading
- Graph validation (check)
- Graph coarsening
- Ghost edge computation (ghst)

---

## Running Benchmarks

### Prerequisites

1. **Build PyScotch:**
   ```bash
   make build-all
   pip install -e .
   ```

2. **For comparison with native Scotch:**
   ```bash
   sudo apt-get install scotch  # Ubuntu/Debian
   ```

3. **For MPI benchmarks:**
   ```bash
   sudo apt-get install openmpi-bin libopenmpi-dev
   ```

### Sequential Benchmarks

```bash
cd benchmarks
python benchmark_sequential_partitioning.py ../external/scotch/src/check/data/bump.grf 4
```

### Distributed Benchmarks

```bash
cd benchmarks
mpirun -np 4 python benchmark_distributed_operations.py ../external/scotch/src/check/data/bump.grf
```

---

## Interpreting Results

### Sequential Partitioning

**Good performance:**
- PyScotch overhead < 25% vs native Scotch
- Imbalance < 10%

**Example output:**
```
PyScotch overhead: +15.2%
✓ Good! PyScotch has acceptable overhead

Partition Quality:
  Imbalance: 5.3%
  ✓ Good balance
```

### Distributed Operations

**Typical times** (for small graphs on 4 processes):
- Load: 1-10 ms
- Check: 0.1-1 ms
- Coarsen: 5-50 ms
- Ghost: 1-5 ms

**Scaling:**
- Times should scale reasonably with graph size
- MPI overhead should be minimal for small process counts

---

## Test Data

Use graphs from `external/scotch/src/check/data/`:
- `bump.grf` - Small (fast benchmarking)
- `bump_b100000.grf` - Large (realistic workloads)
- `m4x4.grf` - Mesh graph

---

## Contributing

Add new benchmarks by:
1. Creating `benchmark_<feature>.py`
2. Following the existing structure
3. Documenting in this README
4. Testing with different graph sizes

---

## Notes

- Benchmark results depend on hardware, system load, and graph structure
- Run multiple iterations for stable averages
- Compare relative performance, not absolute times
- MPI benchmarks require consistent network/IPC performance

---

**Questions?** Open an issue on GitHub!
