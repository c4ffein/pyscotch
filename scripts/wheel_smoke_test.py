"""Smoke test for an installed pyscotch binary wheel.

Run from a directory OUTSIDE the repo checkout so that `import pyscotch`
resolves to the installed wheel, e.g.:

    PYSCOTCH_PARALLEL=0 PYSCOTCH_INT_SIZE=64 python wheel_smoke_test.py
"""

import os

int_size = os.environ.get("PYSCOTCH_INT_SIZE", "32")

import pyscotch  # noqa: E402
from pyscotch import Graph  # noqa: E402

# The wheel must serve the libraries from its bundled pyscotch/_libs directory.
lib_dir = str(pyscotch.libscotch._get_lib_dir())
assert "_libs" in lib_dir or os.environ.get("PYSCOTCH_LIB_DIR"), (
    f"Expected bundled libraries from the wheel, got: {lib_dir}"
)

edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3), (2, 4), (4, 5), (5, 3)]
graph = Graph.from_edges(edges)
parts = graph.partition(2)

assert len(parts) == 6, f"Expected 6 assignments, got: {parts!r}"
assert set(int(p) for p in parts) == {0, 1}, f"Expected both parts used, got: {parts!r}"

# The wheel's `pyscotch` console script must work too — broken entry-point
# wiring would pass every import-based check above.
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

cli = Path(sys.executable).parent / "pyscotch"
assert cli.is_file(), f"console script not installed next to {sys.executable}"
subprocess.run([str(cli), "doctor"], check=True, env=os.environ)
graph.save("smoke.grf")
subprocess.run([str(cli), "partition", "smoke.grf", "-n", "2", "-o", "smoke.map"], check=True, env=os.environ)
assert Path("smoke.map").is_file(), "CLI partition produced no mapping file"

print(f"OK: int_size={int_size} lib_dir={lib_dir} parts={[int(p) for p in parts]}")
