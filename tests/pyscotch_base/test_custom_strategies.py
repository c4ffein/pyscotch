"""
Tests for custom strategy strings.

These tests validate that PyScotch correctly handles custom strategy strings
using Scotch's strategy language syntax. The syntax examples are taken from
Scotch's own source code (library_graph_map.c).
"""

import pytest
import numpy as np
from pyscotch import Graph, Strategy, Strategies


class TestCustomStrategies:
    """Test custom strategy string functionality."""

    @pytest.fixture
    def simple_graph(self):
        """Create a simple test graph."""
        # Ring graph: 0-1-2-3-4-5-0
        edges = [(i, (i + 1) % 20) for i in range(20)]
        return Graph.from_edges(edges, num_vertices=20)

    def test_default_strategy_none(self, simple_graph):
        """Test that None strategy uses Scotch defaults."""
        strategy = Strategies.partition_quality()
        partitions = simple_graph.partition(4, strategy)

        assert len(partitions) == 20
        assert partitions.min() >= 0
        assert partitions.max() < 4

    def test_simple_strategy_strings(self, simple_graph):
        """Test basic strategy strings that Scotch accepts."""
        test_strategies = [
            ("r", "recursive bisection"),
            ("m", "multilevel"),
        ]

        for strat_string, description in test_strategies:
            strategy = Strategy()
            strategy.set_mapping(strat_string)

            partitions = simple_graph.partition(4, strategy)

            assert len(partitions) == 20, f"Failed for {description}"
            assert partitions.min() >= 0, f"Failed for {description}"
            assert partitions.max() < 4, f"Failed for {description}"

    def test_uninitialized_strategy_uses_defaults(self, simple_graph):
        """Test that Strategy() without set_mapping() uses Scotch defaults."""
        strategy = Strategy()
        # Don't call set_mapping() - this uses Scotch's adaptive defaults

        partitions = simple_graph.partition(4, strategy)

        assert len(partitions) == 20
        assert partitions.min() >= 0
        assert partitions.max() < 4

    def test_multilevel_with_parameters(self, simple_graph):
        """Test multilevel strategy with vertex threshold parameter."""
        strategy = Strategy()
        # Simple multilevel with vertex threshold
        strategy.set_mapping("m{vert=100}")

        partitions = simple_graph.partition(4, strategy)

        assert len(partitions) == 20
        assert partitions.min() >= 0
        assert partitions.max() < 4

    def test_recursive_with_parameters(self, simple_graph):
        """Test recursive strategy with parameters."""
        strategy = Strategy()
        # Recursive with balanced partitioning
        strategy.set_mapping("r{job=t,map=t,poli=S,bal=0.05}")

        partitions = simple_graph.partition(4, strategy)

        assert len(partitions) == 20
        assert partitions.min() >= 0
        assert partitions.max() < 4

    def test_internal_vs_public_strategy_api(self):
        """
        Document that Scotch has INTERNAL-ONLY strategy methods.

        This test demonstrates that the 'h' method (used in library_graph_map.c)
        is NOT available through the public SCOTCH_stratGraphMap API.

        Scotch has two APIs:
        1. SCOTCH_stratGraphMapBuild() - internal, uses advanced methods like 'h'
        2. SCOTCH_stratGraphMap() - public, parses user strings, does NOT support 'h'

        This is why we set QUALITY_PARTITION=None to let Scotch use its internal
        defaults rather than trying to replicate internal-only syntax.
        """
        strategy = Strategy()

        # This string works INTERNALLY in Scotch (via stratGraphMapBuild):
        # "m{vert=120,low=h{pass=10}f{bal=0.05,move=120},asc=b{...}}"
        #
        # But it FAILS through the public API (via stratGraphMap):
        with pytest.raises(RuntimeError, match="Failed to set mapping strategy"):
            strategy.set_mapping(
                "m{vert=120,low=h{pass=10}f{bal=0.05,move=120},"
                "asc=b{bnd=f{bal=0.05,move=120},org=f{bal=0.05,move=120}}}"
            )

        # This proves that advanced internal methods are not exposed to users,
        # validating our design decision to use None instead of complex strings

    def test_invalid_strategy_raises_error(self):
        """Test that invalid strategy strings raise appropriate errors."""
        strategy = Strategy()

        # Invalid method name should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to set mapping strategy"):
            # 'h' without a following method is invalid
            strategy.set_mapping("m{vert=100,low=h{pass=10},asc=b{}}")

    def test_strategies_class_constants(self):
        """Test that Strategies class constants are correctly defined."""
        assert Strategies.DEFAULT_PARTITION == ""
        assert Strategies.RECURSIVE_BISECTION == "r"
        assert Strategies.MULTILEVEL == "m"
        assert Strategies.QUALITY_PARTITION is None
        assert Strategies.FAST_PARTITION is None

        assert Strategies.DEFAULT_ORDER == ""
        assert Strategies.NESTED_DISSECTION == "n"
        assert Strategies.SIMPLE_ORDER == "s"
        assert Strategies.MINIMUM_FILL == "c"
        assert Strategies.QUALITY_ORDER is None
        assert Strategies.FAST_ORDER is None

    def test_quality_and_fast_strategies_work(self, simple_graph):
        """Test that quality and fast strategy factory methods work."""
        quality_strat = Strategies.partition_quality()
        fast_strat = Strategies.partition_fast()

        quality_parts = simple_graph.partition(4, quality_strat)
        fast_parts = simple_graph.partition(4, fast_strat)

        # Both should produce valid partitions
        for parts in [quality_parts, fast_parts]:
            assert len(parts) == 20
            assert parts.min() >= 0
            assert parts.max() < 4

    def test_ordering_strategies(self):
        """Test ordering strategy strings."""
        from pyscotch import Graph

        # Create a small graph for ordering
        edges = [(i, (i + 1) % 10) for i in range(10)]
        graph = Graph.from_edges(edges, num_vertices=10)

        test_strategies = [
            ("", "default"),
            ("n", "nested dissection"),
            ("s", "simple"),
            ("c", "minimum fill"),
        ]

        for strat_string, description in test_strategies:
            strategy = Strategy()
            strategy.set_ordering(strat_string)

            perm, invp = graph.order(strategy)

            assert len(perm) == 10, f"Failed for {description}"
            assert len(invp) == 10, f"Failed for {description}"
            # Verify it's a valid permutation
            assert sorted(perm) == list(range(10)), f"Failed for {description}"
