"""Save and load a graph file."""
import tempfile
from pathlib import Path
from pyscotch import Graph

edges = [(0, 1), (1, 2), (2, 3), (3, 0)]

with tempfile.TemporaryDirectory() as tmpdir:
    filepath = Path(tmpdir) / "square.grf"

    # Save
    with Graph.from_edges(edges, num_vertices=4) as g:
        g.save(str(filepath))
        orig_size = g.size()

    # Load into a new graph
    with Graph() as g2:
        g2.load(str(filepath))
        assert g2.check()
        assert g2.size() == orig_size

    print(f"Saved and loaded graph: {orig_size[0]} vertices")
