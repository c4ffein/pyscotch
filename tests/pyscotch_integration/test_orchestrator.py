"""
Integration Test Orchestrator

Runs all integration workflow scripts in isolated subprocesses to prevent
segfaults or other crashes from affecting the test suite.
"""
import os
import subprocess
import sys
from pathlib import Path
import pytest

# CI environments may have fewer CPU slots than requested MPI processes.
# Set PYSCOTCH_MPI_OVERSUBSCRIBE=1 to add --oversubscribe flag.
# WARNING: This doesn't reflect real multi-node MPI behavior.
MPI_OVERSUBSCRIBE = os.environ.get("PYSCOTCH_MPI_OVERSUBSCRIBE", "0") == "1"


def _get_ptscotch_env() -> dict:
    """Get environment variables for PT-Scotch (64-bit, parallel)."""
    env = os.environ.copy()
    env["PYSCOTCH_INT_SIZE"] = "64"
    env["PYSCOTCH_PARALLEL"] = "1"
    return env


def run_workflow_script(script_name: str, num_processes: int = 1, timeout: int = 10) -> tuple[int, str, str]:
    """
    Run an integration workflow script.

    Args:
        script_name: Name of the script file (e.g., "sequential_partitioning_workflow.py")
        num_processes: Number of MPI processes (1 for non-MPI scripts)
        timeout: Timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        raise FileNotFoundError(f"Workflow script not found: {script_path}")

    if num_processes > 1:
        # MPI test - use PT-Scotch environment
        cmd = ["mpirun"]
        if MPI_OVERSUBSCRIBE:
            cmd.append("--oversubscribe")
        cmd.extend(["-np", str(num_processes), sys.executable, str(script_path)])
        env = _get_ptscotch_env()
    else:
        # Regular test - use default environment
        cmd = [sys.executable, str(script_path)]
        env = None

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=Path(__file__).parent.parent.parent,  # Run from repo root
        env=env
    )

    return result.returncode, result.stdout, result.stderr


class TestSequentialPartitioningWorkflow:
    """Sequential graph partitioning integration tests."""

    def test_sequential_partitioning_workflow(self):
        """Test complete sequential partitioning workflow."""
        returncode, stdout, stderr = run_workflow_script("orchestrated_sequential_partitioning.py")

        # Print output for debugging
        if stdout:
            print("STDOUT:", stdout)
        if stderr:
            print("STDERR:", stderr)

        # Check that the script succeeded
        assert returncode == 0, f"Sequential partitioning workflow failed with exit code {returncode}"
        assert "PASS" in stdout or "passed" in stdout.lower(), \
            "Expected success indicator in output"


class TestMeshPartitioningWorkflow:
    """Mesh partitioning integration tests."""

    def test_mesh_partitioning_workflow(self):
        """Test complete mesh partitioning workflow."""
        returncode, stdout, stderr = run_workflow_script("orchestrated_mesh_partitioning.py")

        # Print output for debugging
        if stdout:
            print("STDOUT:", stdout)
        if stderr:
            print("STDERR:", stderr)

        # Check that the script succeeded
        assert returncode == 0, f"Mesh partitioning workflow failed with exit code {returncode}"
        assert "PASS" in stdout or "passed" in stdout.lower(), \
            "Expected success indicator in output"


class TestDistributedCoarseningWorkflow:
    """Distributed coarsening integration tests (MPI)."""

    def test_distributed_coarsening_workflow(self):
        """Test complete distributed coarsening workflow with MPI."""
        # This test uses the existing distributed_coarsening_workflow.py
        returncode, stdout, stderr = run_workflow_script("distributed_coarsening_workflow.py", num_processes=3)

        # Print output for debugging
        if stdout:
            print("STDOUT:", stdout)
        if stderr:
            print("STDERR:", stderr)

        # Check that the script succeeded
        assert returncode == 0, f"Distributed coarsening workflow failed with exit code {returncode}"
        assert "PASS" in stdout, "Expected PASS message in output"
