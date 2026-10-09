"""Pytest configuration for doc examples.

Each ex_*.py and demo_*.py file is collected as a test. They're standalone
scripts that use assertions — if they run without error, the test passes.

The demo_* files are the full demo-walkthrough scripts (see the demo page):
they write files into their working directory by design, so they run in a
throwaway cwd; demo_*parallel* runs with PYSCOTCH_PARALLEL=1 and SKIPS when
the environment has no PT-Scotch build or no mpi4py (an environment
condition, mirroring the doctor's view — any other failure still fails).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent

# Error signatures that mean "this environment cannot run a parallel demo",
# not "the demo is broken".
_PARALLEL_ENV_MISSING = (
    "No module named 'mpi4py'",
    "No Scotch library found",
    "requires PT-Scotch",
)


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".py" and file_path.name.startswith(("ex_", "demo_")):
        return ExampleFile.from_parent(parent, path=file_path)


class ExampleFile(pytest.File):
    def collect(self):
        yield ExampleItem.from_parent(self, name=self.path.stem)


class ExampleItem(pytest.Item):
    def runtest(self):
        is_demo = self.path.name.startswith("demo_")
        wants_parallel = is_demo and "parallel" in self.path.name
        env = os.environ.copy()
        env.setdefault("PYSCOTCH_INT_SIZE", "64")
        if wants_parallel:
            env["PYSCOTCH_PARALLEL"] = "1"
        else:
            env.setdefault("PYSCOTCH_PARALLEL", "0")
        with tempfile.TemporaryDirectory() as demo_cwd:
            result = subprocess.run(
                [sys.executable, str(self.path)],
                capture_output=True,
                text=True,
                env=env,
                # Demos write files into their cwd by design -> throwaway dir
                cwd=demo_cwd if is_demo else str(Path(__file__).parents[3]),
            )
        if result.returncode != 0:
            output = result.stdout + result.stderr
            if wants_parallel and any(sig in output for sig in _PARALLEL_ENV_MISSING):
                pytest.skip(f"environment cannot run the parallel demo: {output.strip().splitlines()[-1]}")
            raise ExampleError(output)

    def repr_failure(self, excinfo, style=None):
        return str(excinfo.value)

    def reportinfo(self):
        return self.path, None, f"example: {self.path.name}"


class ExampleError(Exception):
    pass
