"""
Orchestration tests for PT-Scotch distributed graph operations.

These tests spawn MPI processes using mpirun to execute standalone scripts.
Following the pattern used in the Scotch test suite.
"""
import subprocess
import sys
from pathlib import Path
import pytest

# Directory containing MPI scripts
SCRIPT_DIR = Path(__file__).parent / "mpi_scripts"


def run_mpi_script(script_name: str, num_processes: int = 2) -> tuple[int, str, str]:
    """
    Run a standalone MPI script using mpirun.

    Args:
        script_name: Name of the script file (e.g., "dgraph_init.py")
        num_processes: Number of MPI processes to spawn

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"MPI script not found: {script_path}")

    cmd = ["mpirun", "-np", str(num_processes), sys.executable, str(script_path)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30  # 30 second timeout
    )

    return result.returncode, result.stdout, result.stderr


class TestDgraphInit:
    """Tests for distributed graph initialization."""

    def test_dgraph_init(self):
        """Test basic dgraph initialization and cleanup."""
        returncode, stdout, stderr = run_mpi_script("dgraph_init.py", num_processes=2)

        # Print output for debugging
        if stdout:
            print("STDOUT:", stdout)
        if stderr:
            print("STDERR:", stderr)

        # Check that the script succeeded
        assert returncode == 0, f"MPI script failed with return code {returncode}"
        assert "PASS" in stdout, "Expected PASS message in output"


class TestDgraphBuild:
    """Tests for distributed graph building."""

    def test_dgraph_build(self):
        """Test building a distributed graph from local data."""
        returncode, stdout, stderr = run_mpi_script("dgraph_build.py", num_processes=2)

        # Print output for debugging
        if stdout:
            print("STDOUT:", stdout)
        if stderr:
            print("STDERR:", stderr)

        # Check that the script succeeded
        assert returncode == 0, f"MPI script failed with return code {returncode}"
        assert "PASS" in stdout, "Expected PASS message in output"


class TestDgraphCheck:
    """Tests for distributed graph consistency checking."""

    def test_dgraph_check_empty(self):
        """Test checking empty distributed graph."""
        returncode, stdout, stderr = run_mpi_script("dgraph_check.py", num_processes=2)

        # Print output for debugging
        if stdout:
            print("STDOUT:", stdout)
        if stderr:
            print("STDERR:", stderr)

        # Check that the script succeeded
        assert returncode == 0, f"MPI script failed with return code {returncode}"
        assert "PASS" in stdout, "Expected PASS message in output"

    def test_dgraph_check_real_bump(self):
        """Test checking real distributed graph (bump.grf) - port of Scotch test."""
        # This is a direct port of test_scotch_dgraph_check.c
        script_path = SCRIPT_DIR / "dgraph_check_real.py"
        graph_path = Path("external/scotch/src/check/data/bump.grf")

        cmd = ["mpirun", "-np", "2", sys.executable, str(script_path), str(graph_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Print output for debugging
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check that the script succeeded
        assert result.returncode == 0, f"MPI script failed with return code {result.returncode}"
        assert "PASS" in result.stdout, "Expected PASS message in output"


class TestDgraphCoarsen:
    """Tests for distributed graph coarsening."""

    def test_dgraph_coarsen_bump(self):
        """Test coarsening with bump.grf - port of test_scotch_dgraph_coarsen.c"""
        script_path = SCRIPT_DIR / "dgraph_coarsen.py"
        graph_path = Path("external/scotch/src/check/data/bump.grf")

        # Use 3 processes as in the original Scotch test
        cmd = ["mpirun", "-np", "3", sys.executable, str(script_path), str(graph_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Print output for debugging
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check that the script succeeded
        assert result.returncode == 0, f"MPI script failed with return code {result.returncode}"
        assert "PASS" in result.stdout, "Expected PASS message in output"

    def test_dgraph_coarsen_bump_b100000(self):
        """Test coarsening with bump_b100000.grf (different baseval)"""
        script_path = SCRIPT_DIR / "dgraph_coarsen.py"
        graph_path = Path("external/scotch/src/check/data/bump_b100000.grf")

        cmd = ["mpirun", "-np", "3", sys.executable, str(script_path), str(graph_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Print output for debugging
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check that the script succeeded
        assert result.returncode == 0, f"MPI script failed with return code {result.returncode}"
        assert "PASS" in result.stdout, "Expected PASS message in output"

    def test_dgraph_coarsen_m4x4_b1(self):
        """Test coarsening with m4x4_b1.grf (small mesh)"""
        script_path = SCRIPT_DIR / "dgraph_coarsen.py"
        graph_path = Path("external/scotch/src/check/data/m4x4_b1.grf")

        cmd = ["mpirun", "-np", "3", sys.executable, str(script_path), str(graph_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Print output for debugging
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check that the script succeeded
        assert result.returncode == 0, f"MPI script failed with return code {result.returncode}"
        assert "PASS" in result.stdout, "Expected PASS message in output"
