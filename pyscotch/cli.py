#!/usr/bin/env python3
"""
Command-line interface for PyScotch.
"""

import argparse
import sys

# NOTE: Scotch-touching imports (Graph, Mesh, ...) are intentionally done lazily
# inside each command below, not at module top level. Importing them loads the
# Scotch libraries, which would make even `pyscotch doctor` / `pyscotch --help`
# crash on a broken install — exactly when the user needs the diagnostics.


def partition_graph(args):
    """Partition a graph."""
    from .graph import Graph
    from .strategy import Strategy, Strategies
    from .mapping import Mapping

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
    from .graph import Graph
    from .strategy import Strategy, Strategies
    from .ordering import Ordering

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
    from .mesh import Mesh
    from .strategy import Strategy, Strategies
    from .mapping import Mapping

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
    from .graph import Graph

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


def doctor(args):
    """Report the PyScotch environment and how to fix what's missing."""
    from . import doctor as _doctor

    return _doctor.run(as_json=args.json)


def scotch_manage(args):
    """Dispatch `pyscotch scotch <build|list|use|rm>`."""
    from . import scotch_build

    if args.scotch_command == "build":
        return scotch_build.cmd_build(args)
    if args.scotch_command == "list":
        return scotch_build.cmd_list(args)
    if args.scotch_command == "patches":
        return scotch_build.cmd_patches(args)
    if args.scotch_command == "use":
        return scotch_build.cmd_use(args)
    if args.scotch_command == "rm":
        return scotch_build.cmd_rm(args)
    # No sub-command: show this group's help.
    args._scotch_parser.print_help()
    return 1


def info_graph(args):
    """Display information about a graph."""
    from .graph import Graph

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
    partition_parser.add_argument(
        "-n", "--nparts", type=int, required=True, help="Number of partitions"
    )
    partition_parser.add_argument(
        "-o", "--output", help="Output file (default: <input>.part.<nparts>)"
    )
    partition_parser.add_argument(
        "-s",
        "--strategy",
        choices=["default", "quality", "fast", "multilevel", "recursive"],
        default="default",
        help="Partitioning strategy",
    )
    partition_parser.add_argument(
        "-t", "--type", choices=["graph", "mesh"], default="graph", help="Input file type"
    )
    partition_parser.set_defaults(
        func=lambda args: partition_mesh(args) if args.type == "mesh" else partition_graph(args)
    )

    # Graph order command
    order_parser = subparsers.add_parser("order", help="Order a graph")
    order_parser.add_argument("input", help="Input graph file")
    order_parser.add_argument("-o", "--output", help="Output file (default: <input>.ord)")
    order_parser.add_argument(
        "-s",
        "--strategy",
        choices=["default", "quality", "fast", "nested"],
        default="default",
        help="Ordering strategy",
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

    # Doctor command
    doctor_parser = subparsers.add_parser(
        "doctor", help="Diagnose the PyScotch/Scotch environment and suggest fixes"
    )
    doctor_parser.add_argument(
        "--json", action="store_true", help="Emit the report as JSON for scripts"
    )
    doctor_parser.set_defaults(func=doctor)

    # Scotch management: download/compile/select local Scotch builds
    scotch_parser = subparsers.add_parser(
        "scotch", help="Download, build and manage local Scotch libraries"
    )
    scotch_sub = scotch_parser.add_subparsers(dest="scotch_command", title="scotch commands")
    scotch_parser.set_defaults(func=scotch_manage, _scotch_parser=scotch_parser)

    sb = scotch_sub.add_parser("build", help="Download and compile a Scotch version")
    sb.add_argument("version", nargs="?", default="7.0.11", help="Scotch version (default: 7.0.11)")
    sb.add_argument(
        "-i", "--int-size", choices=["32", "64"], default="64", help="Integer width (default: 64)"
    )
    mode = sb.add_mutually_exclusive_group()
    mode.add_argument("--parallel", action="store_true", help="Also build PT-Scotch (needs MPI)")
    mode.add_argument("--sequential", action="store_true", help="Sequential only (no MPI)")
    sb.add_argument("--use", action="store_true", help="Set as default after building")
    sb.add_argument("--force", action="store_true", help="Rebuild even if it exists")
    sb.add_argument(
        "--pristine",
        action="store_true",
        help="Do NOT apply bundled quickfix patches (upstream may fail to build)",
    )
    sb.add_argument("--url", help="Override the source tarball URL")
    sb.add_argument("--sha256", help="Override/skip the pinned checksum")

    sl = scotch_sub.add_parser("list", help="List locally built Scotch libraries")
    sl.set_defaults()

    scotch_sub.add_parser("patches", help="List bundled Scotch build quickfix patches")

    su = scotch_sub.add_parser("use", help="Set the default local Scotch build")
    su.add_argument("key", help="Build key, e.g. 7.0.11-64-par")

    sr = scotch_sub.add_parser("rm", help="Remove a local Scotch build")
    sr.add_argument("key", help="Build key, e.g. 7.0.11-64-par")

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
