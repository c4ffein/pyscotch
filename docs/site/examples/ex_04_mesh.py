"""Mesh operations: load, convert to graph, partition."""
from pathlib import Path
from pyscotch import Mesh, Mapping, random_reset

# Load a mesh from Scotch's test data
mesh_path = Path("external/scotch/src/check/data/small2.msh")
assert mesh_path.exists(), (
    f"Mesh file not found: {mesh_path}. "
    "Run 'git submodule update --init --recursive' to fetch test data."
)

with Mesh() as mesh:
    mesh.load(mesh_path)
    assert mesh.check(), "Mesh should be valid"

    # Convert mesh to graph
    with mesh.to_graph() as graph:
        assert graph.check()
        v, e = graph.size()
        print(f"Mesh dual graph: {v} vertices, {e} edge entries")
        assert v > 0

    # Partition the mesh into 2 parts
    random_reset()
    parts = mesh.partition(nparts=2)
    mapping = Mapping(parts)
    print(f"Mesh partition sizes: {mapping.get_partition_sizes()}")
    assert mapping.num_partitions() == 2
