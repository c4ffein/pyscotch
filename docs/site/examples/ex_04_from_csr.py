"""Build a graph from CSR arrays."""
import numpy as np
from pyscotch import Graph

# Star graph: vertex 0 connected to 1,2,3,4
# Vertex 0: neighbors [1,2,3,4] -> 4 edges
# Vertices 1-4: neighbor [0] -> 1 edge each
verttab = np.array([0, 4, 5, 6, 7, 8], dtype=np.int64)
edgetab = np.array([1, 2, 3, 4, 0, 0, 0, 0], dtype=np.int64)

with Graph() as graph:
    graph.build(verttab, edgetab)
    assert graph.check()

    vertnbr, edgenbr = graph.size()
    assert vertnbr == 5
    assert edgenbr == 8  # 4 edges * 2 directions
    print(f"Star graph: center vertex with {edgenbr // 2} spokes")
