"""Full workflow: create, save, load, partition, save mapping."""
import tempfile
from pathlib import Path
import numpy as np
from pyscotch import Graph, Mapping, random_reset

edges = [(i, i + 1) for i in range(19)]  # path graph with 20 vertices
edges.append((19, 0))  # close the cycle

with tempfile.TemporaryDirectory() as tmpdir:
    graph_path = Path(tmpdir) / "cycle20.grf"
    map_path = Path(tmpdir) / "cycle20.map"

    # Create and save graph
    with Graph.from_edges(edges, num_vertices=20) as g:
        g.save(str(graph_path))

    # Load, partition, save mapping
    with Graph() as g:
        g.load(str(graph_path))
        random_reset()
        parts = g.partition(nparts=4)
        g.save_mapping(str(map_path), parts)

    # Load and verify mapping
    mapping = Mapping.load(str(map_path))
    assert len(mapping) == 20
    assert mapping.num_partitions() == 4
    print(f"Roundtrip complete: {len(mapping)} vertices, {mapping.num_partitions()} parts")
    print(f"Balance: {mapping.balance():.2f}")
