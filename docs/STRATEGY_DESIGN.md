# Strategy Design Documentation

## Overview

The `Strategies` class provides convenient presets for graph partitioning and ordering operations. This document explains the design decisions and how to use custom strategies.

## Design Philosophy

### Use Scotch's Built-in Defaults

The recommended approach is to let Scotch use its **intelligent adaptive defaults** by passing `None` or an uninitialized `Strategy()`:

```python
from pyscotch import Graph, Strategies

graph = Graph()
graph.load("graph.grf")

# Recommended: Use Scotch's adaptive defaults
strategy = Strategies.partition_quality()  # Returns Strategy() without set_mapping()
partitions = graph.partition(4, strategy)

# Or even simpler:
partitions = graph.partition(4)  # Uses defaults automatically
```

### Why None Instead of Complex Strings?

The original code attempted to hardcode complex strategy strings like:
```python
QUALITY_PARTITION = "m{vert=100,low=h{pass=10},asc=b{...}}"  # BROKEN - syntax error
```

**Problems with this approach:**

1. **Syntax errors**: The original strings had bugs (missing method chaining after `h{pass=10}`)
2. **Version-dependent**: Scotch's strategy syntax evolves between versions
3. **Context-dependent**: Optimal parameters depend on graph size, structure, and hardware
4. **Maintenance burden**: We'd need to keep these strings in sync with Scotch updates

**Solution:** Set quality/fast strategies to `None` and let Scotch decide.

## How Scotch Handles Strategies

### Internal Strategy Building

When you use Scotch's C API with quality flags, it builds complex strategies internally:

```c
// From library_graph_map.c
SCOTCH_stratGraphMapBuild(&strat, SCOTCH_STRATQUALITY, nparts, balance);
// This internally builds:
// "m{vert=120,low=h{pass=10}f{bal=0.05,move=120},asc=b{...}}"
```

Scotch considers:
- Graph size (vertex count, edge count)
- Number of partitions
- Balance requirements
- Platform capabilities

### Strategy Initialization Modes

1. **`SCOTCH_stratInit()` only** - Uses Scotch's adaptive defaults (recommended)
2. **`SCOTCH_stratGraphMapBuild()`** - Uses predefined templates with flags
3. **`SCOTCH_stratGraphMap()` with string** - Custom strategy string

PyScotch's `Strategy()` without `set_mapping()` corresponds to mode 1.

## Custom Strategy Strings

For advanced users who need fine-grained control, custom strategy strings can be provided.

### Basic Syntax

```python
from pyscotch import Strategy

strategy = Strategy()
strategy.set_mapping("r")  # Recursive bisection
# or
strategy.set_mapping("m")  # Multilevel
```

### Strategy String Reference

| String | Method | Description |
|--------|--------|-------------|
| `""`   | Default | Scotch's adaptive defaults |
| `"r"`  | Recursive bisection | Fast, reasonable quality |
| `"m"`  | Multilevel | Better quality, slower |
| `"n"`  | Nested dissection | For ordering |
| `"s"`  | Simple | Fast ordering |
| `"c"`  | Minimum fill | For ordering |

### Advanced Syntax

Complex strategies follow this pattern:
```
method{param1=value1,param2=value2,...}
```

Methods can be **chained** together (no spaces):
```
"m{vert=120,low=h{pass=10}f{bal=0.05,move=120},asc=b{...}}"
              ^^^^^^^^^^^^^ h and f are chained, no comma between them
```

**Key insight from Scotch source:** After `h{pass=10}` you **must** chain another method like `f{...}` (Fiduccia-Mattheyses). The original pyscotch code had `h{pass=10},` which is invalid.

### Working Examples from Scotch

From `external/scotch/src/libscotch/library_graph_map.c`:

```c
// Recursive with parameters
"r{job=t,map=t,poli=S,bal=0.05}"

// Multilevel with chained methods
"m{vert=120,low=h{pass=10}f{bal=0.05,move=120},asc=b{bnd=f{bal=0.05,move=120}}}"
```

## Testing Custom Strategies

See `tests/pyscotch_base/test_custom_strategies.py` for examples:

```python
def test_custom_strategy():
    strategy = Strategy()
    # Multilevel with vertex threshold
    strategy.set_mapping("m{vert=100}")

    partitions = graph.partition(4, strategy)
    # ...validate results...
```

## Migration Guide

If you were using the old `Strategies.partition_quality()`:

### Before (Broken)
```python
strategy = Strategies.partition_quality()
# This tried to use: "m{vert=100,low=h{pass=10},...}"  # INVALID SYNTAX
```

### After (Fixed)
```python
strategy = Strategies.partition_quality()
# Now returns: Strategy() without set_mapping() - uses Scotch's adaptive defaults
```

**Result:** Better quality partitions because Scotch's internal heuristics are more sophisticated than any hardcoded string.

## References

- Scotch strategy source: `external/scotch/src/libscotch/library_graph_map.c`
- Scotch documentation: `external/scotch/doc/scotch_user7.0.pdf`
- Test examples: `external/scotch/src/check/test_scotch_graph_map.c`
- PyScotch tests: `tests/pyscotch_base/test_custom_strategies.py`

## Summary

| Approach | When to Use | Example |
|----------|-------------|---------|
| **None/default** | Most users (recommended) | `graph.partition(4)` |
| **Simple strings** | Basic control over method | `strategy.set_mapping("r")` |
| **Complex strings** | Advanced tuning (experts only) | `strategy.set_mapping("m{vert=120,...}")` |

**Recommendation:** Start with defaults. Only use custom strategies if profiling shows a need and you understand Scotch's strategy language.
