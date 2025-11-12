# Hypothesis Property-Based Tests

This directory will contain property-based tests using the [Hypothesis](https://hypothesis.readthedocs.io/) framework.

## Future Test Ideas

Property-based tests can verify invariants that should hold for ANY input:

### Graph Operations
- **Partition validity**: All vertices assigned to a partition, partitions cover full range
- **Ordering validity**: Permutation is bijective, inverse is correct
- **Coloring validity**: No adjacent vertices have same color
- **Graph symmetry**: Operations should work on any valid graph structure

### Multi-variant Consistency
- **Cross-variant agreement**: 32-bit and 64-bit should produce same partitions
- **Determinism**: Same graph + same strategy = same result

### Performance Properties
- **Complexity bounds**: Operations complete in reasonable time
- **Memory bounds**: No unexpected memory growth

## Installation

```bash
pip install hypothesis
```

## Running

```bash
pytest tests/hypothesis/ -v
```

Stay tuned! 🚀
