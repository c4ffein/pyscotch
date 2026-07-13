"""Pytest configuration for doc examples.

Each ex_*.py file is collected as a test. They're standalone scripts
that use assertions — if they run without error, the test passes.
"""
import subprocess
import sys
import os

import pytest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent


def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".py" and file_path.name.startswith("ex_"):
        return ExampleFile.from_parent(parent, path=file_path)


class ExampleFile(pytest.File):
    def collect(self):
        yield ExampleItem.from_parent(self, name=self.path.stem)


class ExampleItem(pytest.Item):
    def runtest(self):
        env = os.environ.copy()
        env.setdefault("PYSCOTCH_INT_SIZE", "64")
        env.setdefault("PYSCOTCH_PARALLEL", "0")
        result = subprocess.run(
            [sys.executable, str(self.path)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(Path(__file__).parents[3]),  # project root
        )
        if result.returncode != 0:
            raise ExampleError(result.stdout + result.stderr)

    def repr_failure(self, excinfo, style=None):
        return str(excinfo.value)

    def reportinfo(self):
        return self.path, None, f"example: {self.path.name}"


class ExampleError(Exception):
    pass
