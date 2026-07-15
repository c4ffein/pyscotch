"""Tests for `pyscotch doctor` diagnostics (pyscotch/doctor.py)."""

import json

import pyscotch.doctor as doctor


class TestCollect:
    """The diagnostics dict on the current (working) test environment."""

    def test_collect_has_expected_shape(self):
        info = doctor.collect()
        for key in (
            "pyscotch_version",
            "python",
            "platform",
            "requested",
            "backend",
            "mpi",
            "problems",
        ):
            assert key in info, key

    def test_backend_loaded_in_test_env(self):
        # The test suite runs against a working Scotch, so the backend must load
        # and report a version, integer width and source.
        b = doctor.collect()["backend"]
        assert b["loaded"] is True
        assert b["version"] and b["version"] != "unknown"
        assert b["int_size"] in (32, 64)
        assert b["source"]

    def test_json_serializable(self):
        # `doctor --json` must be able to dump the dict.
        info = doctor.collect()
        json.loads(json.dumps(info))  # round-trips without error


class TestRender:
    def test_render_is_text(self):
        text = doctor.render(doctor.collect())
        assert "PyScotch environment report" in text
        assert "Scotch backend:" in text

    def test_render_handles_failed_backend(self):
        # A synthetic "backend failed to load" dict must render, not crash.
        fake = {
            "pyscotch_version": "0.0.0",
            "python": "3.x",
            "platform": "test",
            "requested": {
                "int_size": "64",
                "parallel": True,
                "PYSCOTCH_SYSTEM": None,
                "PYSCOTCH_LIB_DIR": None,
            },
            "backend": {"loaded": False, "error": "boom"},
            "mpi": {"libmpi": None, "mpi4py": None, "mpi_library": None},
            "problems": [("Scotch failed to load", "install it")],
        }
        text = doctor.render(fake)
        assert "Loaded" in text and "NO" in text
        assert "boom" in text
        assert "install it" in text


class TestHints:
    def test_install_hints_are_strings(self):
        assert isinstance(doctor._scotch_install_hint(False), str)
        assert isinstance(doctor._scotch_install_hint(True), str)
        assert isinstance(doctor._mpi_install_hint(), str)

    def test_backend_source_labels(self):
        req = {"PYSCOTCH_SYSTEM": None, "PYSCOTCH_LIB_DIR": None}
        assert "system" in doctor._backend_source(None, req).lower()
        req_sys = {"PYSCOTCH_SYSTEM": "1", "PYSCOTCH_LIB_DIR": None}
        assert "forced" in doctor._backend_source(None, req_sys).lower()


class TestRun:
    def test_run_returns_zero_on_healthy_env(self, capsys):
        rc = doctor.run(as_json=False)
        out = capsys.readouterr().out
        assert "PyScotch environment report" in out
        # The test env is healthy, so no problems -> exit 0.
        assert rc == 0

    def test_run_json(self, capsys):
        rc = doctor.run(as_json=True)
        out = capsys.readouterr().out
        json.loads(out)  # valid JSON
        assert rc == 0
