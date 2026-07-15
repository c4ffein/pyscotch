"""Tests for the local Scotch build store and helpers (no network / compile)."""

import importlib

import pytest

import pyscotch._store as store
import pyscotch.scotch_build as sb


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """Point the store at an isolated temp home."""
    monkeypatch.setenv("PYSCOTCH_HOME", str(tmp_path))
    importlib.reload(store)
    yield tmp_path
    importlib.reload(store)


def _make_build(home, key, parallel=False):
    info = store.parse_key(key)
    libd = home / "builds" / key / f"lib{info['bits']}"
    libd.mkdir(parents=True)
    (libd / "libscotch.so").write_bytes(b"\x7fELF")
    if parallel:
        (libd / "libptscotch.so").write_bytes(b"\x7fELF")
    return libd


class TestStoreKeys:
    def test_make_and_parse_roundtrip(self):
        key = store.make_key("7.0.11", 64, True)
        assert key == "7.0.11-64-par"
        info = store.parse_key(key)
        assert info == {"version": "7.0.11", "bits": 64, "variant": "par", "parallel": True}

    def test_parse_rejects_garbage(self):
        assert store.parse_key("nonsense") is None
        assert store.parse_key("7.0.11-99-seq") is None
        assert store.parse_key("7.0.11-64-xyz") is None

    def test_home_respects_env(self, tmp_home):
        assert store.home() == tmp_home


class TestStoreListing:
    def test_list_and_default(self, tmp_home):
        assert store.list_keys() == []
        _make_build(tmp_home, "7.0.11-64-seq")
        _make_build(tmp_home, "7.0.10-64-seq")
        assert store.list_keys() == ["7.0.10-64-seq", "7.0.11-64-seq"]

        assert store.get_default_key() is None
        store.set_default_key("7.0.11-64-seq")
        assert store.get_default_key() == "7.0.11-64-seq"
        store.clear_default()
        assert store.get_default_key() is None

    def test_default_ignored_if_build_gone(self, tmp_home):
        store.set_default_key("7.0.11-64-seq")  # never built
        assert store.get_default_key() is None


class TestManagedLibDir:
    def test_matches_width_and_variant(self, tmp_home):
        _make_build(tmp_home, "7.0.11-64-par", parallel=True)
        store.set_default_key("7.0.11-64-par")
        # 64-bit parallel request -> served
        assert store.managed_lib_dir(64, True) is not None
        # 64-bit sequential request -> a par build still has libscotch.so
        assert store.managed_lib_dir(64, False) is not None
        # 32-bit request -> width mismatch, falls through
        assert store.managed_lib_dir(32, False) is None

    def test_seq_build_cannot_serve_parallel(self, tmp_home):
        _make_build(tmp_home, "7.0.11-64-seq", parallel=False)
        store.set_default_key("7.0.11-64-seq")
        assert store.managed_lib_dir(64, False) is not None
        assert store.managed_lib_dir(64, True) is None  # no libptscotch.so

    def test_no_default_returns_none(self, tmp_home):
        _make_build(tmp_home, "7.0.11-64-seq")
        assert store.managed_lib_dir(64, False) is None  # default not set


class TestDiagnosis:
    def test_flex_too_old(self):
        text = "undefined reference to `_SCOTCHyy_64lex'"
        assert "flex" in sb._diagnose_make_output(text).lower()

    def test_rename_table_regression(self):
        text = (
            "library_mesh_f.c:233:14: error: implicit declaration of function "
            "'SCOTCH_meshBuildElem'; did you mean 'SCOTCH_meshBuildElem_64'?"
        )
        hint = sb._diagnose_make_output(text)
        assert "SCOTCH_meshBuildElem" in hint and "rename" in hint.lower()

    def test_zlib_missing_needs_real_signature(self):
        # A bare '-lz' on a command line must NOT be diagnosed as a zlib problem.
        assert sb._diagnose_make_output("gcc ... -lz -lm -lrt ...") == ""
        assert "zlib" in sb._diagnose_make_output("fatal error: zlib.h: No such file").lower()

    def test_unknown_returns_empty(self):
        assert sb._diagnose_make_output("some unrelated failure") == ""


class TestPreflightAndInc:
    def test_preflight_returns_checks(self):
        checks = sb.preflight(parallel=False)
        names = [c.name for c in checks]
        assert "C compiler" in names and "flex >= 2.6.4" in names and "zlib headers" in names
        # parallel adds an mpicc check
        assert any("mpicc" in c.name for c in sb.preflight(parallel=True))

    def test_makefile_inc_uses_compilers(self):
        inc = sb._makefile_inc("clang", "mpicc")
        assert "CCS        = clang" in inc
        assert "CCP        = mpicc" in inc
        assert "SCOTCH_RENAME" in inc
