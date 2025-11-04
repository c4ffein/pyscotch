#!/usr/bin/env python3
"""
Command-line interface for PyScotch.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .graph import Graph
from .mesh import Mesh
from .strategy import Strategy, Strategies
from .mapping import Mapping
from .ordering import Ordering


def partition_graph(args):
    """Partition a graph."""
    print(f"Loading graph from {args.input}...")
    graph = Graph()
    graph.load(args.input)

    vertnbr, edgenbr = graph.size()
    print(f"Graph: {vertnbr} vertices, {edgenbr} edges")

    # Set up strategy
    if args.strategy == "quality":
        strategy = Strategies.partition_quality()
    elif args.strategy == "fast":
        strategy = Strategies.partition_fast()
    elif args.strategy == "multilevel":
        strategy = Strategy()
        strategy.set_multilevel()
    elif args.strategy == "recursive":
        strategy = Strategy()
        strategy.set_recursive_bisection()
    else:
        strategy = Strategy()
        strategy.set_mapping_default()

    print(f"Partitioning into {args.nparts} parts...")
    partitions = graph.partition(args.nparts, strategy)

    # Save results
    output = args.output or f"{args.input}.part.{args.nparts}"
    print(f"Saving partition to {output}...")
    graph.save_mapping(output, partitions)

    # Print statistics
    mapping = Mapping(partitions)
    sizes = mapping.get_partition_sizes()
    print(f"\nPartition statistics:")
    print(f"  Number of parts: {mapping.num_partitions()}")
    print(f"  Balance: {mapping.balance():.3f}")
    print(f"  Min size: {sizes.min()}")
    print(f"  Max size: {sizes.max()}")
    print(f"  Avg size: {sizes.mean():.1f}")

    print("\nDone!")


def order_graph(args):
    """Order a graph."""
    print(f"Loading graph from {args.input}...")
    graph = Graph()
    graph.load(args.input)

    vertnbr, edgenbr = graph.size()
    print(f"Graph: {vertnbr} vertices, {edgenbr} edges")

    # Set up strategy
    if args.strategy == "quality":
        strategy = Strategies.order_quality()
    elif args.strategy == "fast":
        strategy = Strategies.order_fast()
    elif args.strategy == "nested":
        strategy = Strategy()
        strategy.set_nested_dissection()
    else:
        strategy = Strategy()
        strategy.set_ordering_default()

    print(f"Computing ordering...")
    permutation, inverse = graph.order(strategy)

    # Save results
    output = args.output or f"{args.input}.ord"
    print(f"Saving ordering to {output}...")
    ordering = Ordering(permutation, inverse)
    ordering.save(output)

    print("\nDone!")


def partition_mesh(args):
    """Partition a mesh."""
    print(f"Loading mesh from {args.input}...")
    mesh = Mesh()
    mesh.load(args.input)

    # Set up strategy
    if args.strategy == "quality":
        strategy = Strategies.partition_quality()
    elif args.strategy == "fast":
        strategy = Strategies.partition_fast()
    else:
        strategy = Strategy()
        strategy.set_mapping_default()

    print(f"Partitioning into {args.nparts} parts...")
    partitions = mesh.partition(args.nparts, strategy)

    # Save results
    output = args.output or f"{args.input}.part.{args.nparts}"
    print(f"Saving partition to {output}...")
    mesh.save_mapping(output, partitions)

    # Print statistics
    mapping = Mapping(partitions)
    sizes = mapping.get_partition_sizes()
    print(f"\nPartition statistics:")
    print(f"  Number of parts: {mapping.num_partitions()}")
    print(f"  Balance: {mapping.balance():.3f}")
    print(f"  Min size: {sizes.min()}")
    print(f"  Max size: {sizes.max()}")
    print(f"  Avg size: {sizes.mean():.1f}")

    print("\nDone!")


def check_graph(args):
    """Check a graph for consistency."""
    print(f"Loading graph from {args.input}...")
    graph = Graph()
    graph.load(args.input)

    vertnbr, edgenbr = graph.size()
    print(f"Graph: {vertnbr} vertices, {edgenbr} edges")

    print("Checking graph consistency...")
    if graph.check():
        print("Graph is valid!")
        return 0
    else:
        print("Graph is INVALID!")
        return 1


def info_graph(args):
    """Display information about a graph."""
    print(f"Loading graph from {args.input}...")
    graph = Graph()
    graph.load(args.input)

    vertnbr, edgenbr = graph.size()
    print(f"\nGraph Information:")
    print(f"  Vertices: {vertnbr}")
    print(f"  Edges: {edgenbr}")
    print(f"  Average degree: {edgenbr / vertnbr:.2f}")

    if graph.check():
        print(f"  Status: Valid")
    else:
        print(f"  Status: INVALID")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PyScotch - Python wrapper for PT-Scotch graph partitioning library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(title="commands", dest="command", help="Available commands")

    # Graph partition command
    partition_parser = subparsers.add_parser("partition", help="Partition a graph or mesh")
    partition_parser.add_argument("input", help="Input graph/mesh file")
    partition_parser.add_argument("-n", "--nparts", type=int, required=True, help="Number of partitions")
    partition_parser.add_argument("-o", "--output", help="Output file (default: <input>.part.<nparts>)")
    partition_parser.add_argument(
        "-s", "--strategy",
        choices=["default", "quality", "fast", "multilevel", "recursive"],
        default="default",
        help="Partitioning strategy"
    )
    partition_parser.add_argument(
        "-t", "--type",
        choices=["graph", "mesh"],
        default="graph",
        help="Input file type"
    )
    partition_parser.set_defaults(func=lambda args: partition_mesh(args) if args.type == "mesh" else partition_graph(args))

    # Graph order command
    order_parser = subparsers.add_parser("order", help="Order a graph")
    order_parser.add_argument("input", help="Input graph file")
    order_parser.add_argument("-o", "--output", help="Output file (default: <input>.ord)")
    order_parser.add_argument(
        "-s", "--strategy",
        choices=["default", "quality", "fast", "nested"],
        default="default",
        help="Ordering strategy"
    )
    order_parser.set_defaults(func=order_graph)

    # Check command
    check_parser = subparsers.add_parser("check", help="Check graph consistency")
    check_parser.add_argument("input", help="Input graph file")
    check_parser.set_defaults(func=check_graph)

    # Info command
    info_parser = subparsers.add_parser("info", help="Display graph information")
    info_parser.add_argument("input", help="Input graph file")
    info_parser.set_defaults(func=info_graph)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    try:
        result = args.func(args)
        return result if result is not None else 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
