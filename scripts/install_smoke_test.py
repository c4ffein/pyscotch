"""Install-method-agnostic smoke test for an installed pyscotch.

Unlike scripts/wheel_smoke_test.py (which asserts the libraries came bundled
inside a wheel), this one only checks that pyscotch imports and works — from
wherever it found Scotch (bundled wheel, system package, or conda). Run from a
directory OUTSIDE the repo so `import pyscotch` resolves to the install:

    PYSCOTCH_PARALLEL=0 python install_smoke_test.py
"""

import os
import subprocess
import sys
from pathlib import Path

import pyscotch
from pyscotch import Graph

version = pyscotch.scotch_version()
assert len(version) == 3, f"unexpected version tuple: {version!r}"

lib_dir = pyscotch.libscotch._lib_dir  # None for a system-loaded Scotch

edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3), (2, 4), (4, 5), (5, 3)]
graph = Graph.from_edges(edges)
parts = graph.partition(2)
assert len(parts) == 6, f"expected 6 assignments, got {parts!r}"
assert set(int(p) for p in parts) == {0, 1}, f"expected both parts used, got {parts!r}"

# ordering exercises the FILE*-free path too
perm = graph.order()[0]
assert sorted(int(p) for p in perm) == list(range(6)), f"bad permutation {perm!r}"

# The `pyscotch` console script must work too — a wheel/sdist with broken
# entry-point wiring passes every `import pyscotch` check above. Resolve it
# next to the running interpreter so this works without an activated venv
# (uv-created envs, `micromamba run`, ...).
cli = Path(sys.executable).parent / "pyscotch"
assert cli.is_file(), f"console script not installed next to {sys.executable}"
subprocess.run([str(cli), "doctor"], check=True)
graph.save("smoke.grf")
subprocess.run([str(cli), "partition", "smoke.grf", "-n", "2", "-o", "smoke.map"], check=True)
assert Path("smoke.map").is_file(), "CLI partition produced no mapping file"

int_size = pyscotch.libscotch.get_scotch_int_size()
print(
    f"OK: pyscotch {pyscotch.__version__} on Scotch {'.'.join(map(str, version))}, "
    f"int_size={int_size}, lib_dir={lib_dir!r}, parts={[int(p) for p in parts]}"
)
