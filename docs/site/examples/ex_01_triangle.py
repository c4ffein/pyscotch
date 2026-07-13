"""Build a triangle graph and inspect it."""
import numpy as np
from pyscotch import Graph

# CSR representation of a triangle: 0-1, 0-2, 1-2
verttab = np.array([0, 2, 4, 6], dtype=np.int64)  # vertex start indices
edgetab = np.array([1, 2, 0, 2, 0, 1], dtype=np.int64)  # neighbor lists

with Graph() as graph:
    graph.build(verttab, edgetab)

    assert graph.check(), "Graph should be valid"

    vertnbr, edgenbr = graph.size()
    assert vertnbr == 3, f"Expected 3 vertices, got {vertnbr}"
    assert edgenbr == 6, f"Expected 6 edge entries, got {edgenbr}"

    print(f"Triangle graph: {vertnbr} vertices, {edgenbr} edge entries")
