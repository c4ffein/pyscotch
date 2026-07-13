"""Create a graph from an edge list."""
from pyscotch import Graph

# A pentagon: 0-1-2-3-4-0
edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)]

with Graph.from_edges(edges, num_vertices=5) as graph:
    assert graph.check()
    vertnbr, edgenbr = graph.size()
    # 5 vertices, 10 edge entries (each undirected edge stored twice)
    assert vertnbr == 5
    assert edgenbr == 10
    print(f"Pentagon: {vertnbr} vertices, {edgenbr // 2} edges")
