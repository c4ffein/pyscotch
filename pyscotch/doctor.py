"""
Environment diagnostics for PyScotch — `pyscotch doctor`.

Reports which Scotch backend loaded (and from where), its version / integer
width / capabilities, MPI availability, and concrete commands to fix whatever
is missing. Designed to stay useful when Scotch FAILS to load: every probe is
defensive, so `pyscotch doctor` diagnoses a broken install instead of crashing
with the same import error the user is trying to understand.
"""

import ctypes.util
import os
import platform
from pathlib import Path


# ---------------------------------------------------------------------------
# Probes (never raise; failures become fields / problems)
# ---------------------------------------------------------------------------
def _backend_source(lib_dir, requested):
    """Human label for where the loaded Scotch came from."""
    if requested["PYSCOTCH_SYSTEM"] == "1":
        return "system (forced by PYSCOTCH_SYSTEM=1)"
    if requested["PYSCOTCH_LIB_DIR"]:
        return f"PYSCOTCH_LIB_DIR ({requested['PYSCOTCH_LIB_DIR']})"
    if lib_dir is None:
        return "system (distro/conda, dlopen by soname)"
    p = str(lib_dir)
    try:
        from . import _store

        if str(_store.builds_dir()) in p:
            return f"user-built (pyscotch scotch use {Path(p).parent.name})"
    except Exception:
        pass
    if f"{os.sep}_libs{os.sep}" in p:
        return "bundled wheel libraries"
    if "scotch-builds" in p:
        return "development build (scotch-builds/)"
    return p


def _backend_info(lib, problems):
    """Introspect an already-imported libscotch module."""
    info = {"loaded": True}
    try:
        info["int_size"] = lib.get_scotch_int_size()
        info["parallel"] = lib.is_parallel()
        info["suffix"] = lib._SUFFIX or "(unsuffixed)"
        lib_dir = lib._loaded_lib_dir
        info["lib_dir"] = str(lib_dir) if lib_dir is not None else None
        info["source"] = _backend_source(
            lib_dir,
            {
                "PYSCOTCH_SYSTEM": os.environ.get("PYSCOTCH_SYSTEM"),
                "PYSCOTCH_LIB_DIR": os.environ.get("PYSCOTCH_LIB_DIR"),
            },
        )
    except Exception as e:  # pragma: no cover - defensive
        problems.append(("Could not read backend configuration", str(e)))

    try:
        info["version"] = ".".join(str(v) for v in lib.get_scotch_version())
    except Exception:
        info["version"] = "unknown"

    # Capabilities
    context_available = None
    try:
        context_available = lib._SIZES.get("context") is not None
    except Exception:
        pass
    info["context_available"] = context_available
    if context_available is False:
        problems.append(
            (
                "SCOTCH_Context unavailable (Scotch < 7.0.5)",
                "Use the bundled wheel or conda Scotch, or upgrade the system "
                "Scotch to >= 7.0.5.",
            )
        )

    try:
        info["error_capture"] = lib._err_capture is not None
    except Exception:
        info["error_capture"] = None

    return info


def _mpi_info(parallel_requested, problems):
    """MPI runtime + mpi4py availability."""
    info = {}
    libmpi = ctypes.util.find_library("mpi")
    info["libmpi"] = libmpi

    try:
        import mpi4py
        from mpi4py import MPI

        info["mpi4py"] = mpi4py.__version__
        # First line of the vendor string, e.g. "Open MPI v5.0.7 ...".
        info["mpi_library"] = MPI.Get_library_version().strip().splitlines()[0]
    except ImportError:
        info["mpi4py"] = None
        info["mpi_library"] = None
        if parallel_requested:
            problems.append(
                (
                    "mpi4py not installed (recommended for Dgraph)",
                    "pip install 'pyscotch[parallel]'  (or conda install mpi4py)",
                )
            )

    if parallel_requested and not libmpi and info["mpi4py"] is None:
        problems.append(
            (
                "No MPI runtime found but PYSCOTCH_PARALLEL=1",
                _mpi_install_hint(),
            )
        )
    return info


# ---------------------------------------------------------------------------
# Install hints (distro-aware)
# ---------------------------------------------------------------------------
def _distro_family():
    """'debian', 'fedora', 'conda', 'macos', or None — best effort."""
    if os.environ.get("CONDA_PREFIX"):
        return "conda"
    if platform.system() == "Darwin":
        return "macos"
    try:
        osr = Path("/etc/os-release").read_text()
    except OSError:
        return None
    like = ""
    for line in osr.splitlines():
        if line.startswith(("ID=", "ID_LIKE=")):
            like += " " + line.split("=", 1)[1].strip().strip('"')
    if any(k in like for k in ("debian", "ubuntu")):
        return "debian"
    if any(k in like for k in ("fedora", "rhel", "centos")):
        return "fedora"
    return None


def _scotch_install_hint(parallel):
    fam = _distro_family()
    if fam == "debian":
        return "sudo apt install " + ("libptscotch-dev" if parallel else "libscotch-dev")
    if fam == "fedora":
        return "sudo dnf install " + ("ptscotch-mpich-devel" if parallel else "scotch-devel")
    if fam == "conda":
        return "conda install -c conda-forge " + ("ptscotch mpi4py" if parallel else "scotch")
    if fam == "macos":
        return "brew install scotch" + ("  # (PT-Scotch: build from source)" if parallel else "")
    return "install Scotch from your package manager, or build from source"


def _mpi_install_hint():
    fam = _distro_family()
    if fam == "debian":
        return "sudo apt install libopenmpi-dev openmpi-bin"
    if fam == "fedora":
        return "sudo dnf install openmpi-devel"
    if fam == "conda":
        return "conda install -c conda-forge openmpi  (or mpich)"
    if fam == "macos":
        return "brew install open-mpi"
    return "install an MPI implementation (OpenMPI or MPICH)"


# ---------------------------------------------------------------------------
# Top-level collection
# ---------------------------------------------------------------------------
def collect():
    """Gather the full diagnostics dict. Never raises."""
    from ._version import __version__

    requested = {
        "int_size": os.environ.get("PYSCOTCH_INT_SIZE", "64"),
        "parallel": os.environ.get("PYSCOTCH_PARALLEL", "0") == "1",
        "PYSCOTCH_SYSTEM": os.environ.get("PYSCOTCH_SYSTEM"),
        "PYSCOTCH_LIB_DIR": os.environ.get("PYSCOTCH_LIB_DIR"),
    }
    info = {
        "pyscotch_version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "requested": requested,
    }
    problems = []

    try:
        from . import libscotch as lib

        info["backend"] = _backend_info(lib, problems)
    except Exception as e:
        info["backend"] = {"loaded": False, "error": str(e)}
        problems.append(("Scotch failed to load", _scotch_install_hint(requested["parallel"])))

    info["mpi"] = _mpi_info(requested["parallel"], problems)
    info["problems"] = problems
    return info


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _fmt(label, value):
    return f"  {label:<22} {value}"


def render(info):
    """Render the diagnostics dict as a human-readable report."""
    out = []
    out.append("PyScotch environment report")
    out.append("=" * 40)
    out.append(_fmt("PyScotch version", info["pyscotch_version"]))
    out.append(_fmt("Python", info["python"]))
    out.append(_fmt("Platform", info["platform"]))

    req = info["requested"]
    out.append("")
    out.append("Requested (env):")
    out.append(_fmt("PYSCOTCH_INT_SIZE", req["int_size"]))
    out.append(_fmt("PYSCOTCH_PARALLEL", "1" if req["parallel"] else "0"))
    if req["PYSCOTCH_SYSTEM"]:
        out.append(_fmt("PYSCOTCH_SYSTEM", req["PYSCOTCH_SYSTEM"]))
    if req["PYSCOTCH_LIB_DIR"]:
        out.append(_fmt("PYSCOTCH_LIB_DIR", req["PYSCOTCH_LIB_DIR"]))

    b = info["backend"]
    out.append("")
    out.append("Scotch backend:")
    if not b.get("loaded"):
        out.append(_fmt("Loaded", "NO"))
        out.append(_fmt("Error", b.get("error", "")))
    else:
        out.append(_fmt("Loaded", "yes"))
        out.append(_fmt("Version", b.get("version", "unknown")))
        out.append(_fmt("Source", b.get("source", "?")))
        if b.get("lib_dir"):
            out.append(_fmt("Library dir", b["lib_dir"]))
        out.append(_fmt("Integer width", f"{b.get('int_size')}-bit"))
        out.append(_fmt("Symbol suffix", b.get("suffix", "?")))
        out.append(_fmt("Parallel (PT-Scotch)", "yes" if b.get("parallel") else "no"))
        ctx = b.get("context_available")
        out.append(_fmt("Context (>=7.0.5)", "yes" if ctx else ("no" if ctx is False else "?")))
        out.append(_fmt("Error capture", "active" if b.get("error_capture") else "off"))

    m = info["mpi"]
    out.append("")
    out.append("MPI:")
    out.append(_fmt("libmpi", m.get("libmpi") or "not found"))
    out.append(_fmt("mpi4py", m.get("mpi4py") or "not installed"))
    if m.get("mpi_library"):
        out.append(_fmt("MPI library", m["mpi_library"]))

    out.append("")
    if info["problems"]:
        out.append(f"Problems ({len(info['problems'])}):")
        for symptom, hint in info["problems"]:
            out.append(f"  ✗ {symptom}")
            out.append(f"      → {hint}")
    else:
        out.append("No problems detected. ✓")

    return "\n".join(out)


def run(as_json=False):
    """Entry point for `pyscotch doctor`. Returns a process exit code."""
    info = collect()
    if as_json:
        import json

        print(json.dumps(info, indent=2))
    else:
        print(render(info))
    # Non-zero exit when something is actually wrong, so scripts/CI can gate on it.
    return 1 if info["problems"] else 0
