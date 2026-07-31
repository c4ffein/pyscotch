"""Tests for the local Scotch build store and helpers (no network / compile)."""

import importlib
from pathlib import Path

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


class TestLatestVersion:
    def test_latest_is_numerically_greatest(self):
        assert sb.latest_version() == max(sb._KNOWN_VERSIONS, key=lambda v: tuple(map(int, v.split("."))))

    def test_sorting_is_numeric_not_lexicographic(self, monkeypatch):
        # "7.0.9" > "7.0.10" as strings — the classic trap.
        monkeypatch.setattr(sb, "_KNOWN_VERSIONS", {"7.0.9": "x", "7.0.10": "y"})
        assert sb.latest_version() == "7.0.10"

    def test_latest_pristine_skips_patched_versions(self, monkeypatch):
        monkeypatch.setattr(sb, "_KNOWN_VERSIONS", {"7.0.10": "x", "7.0.11": "y", "7.0.12": "z"})
        monkeypatch.setattr(sb, "_PATCHES", {"7.0.12": [("f.patch", "why")]})
        assert sb.latest_version() == "7.0.12"
        assert sb.latest_pristine_version() == "7.0.11"

    def test_hints_derive_from_the_catalog(self):
        """No hint may hardcode a version: doctor and the loader error must
        recommend whatever the catalog says is latest."""
        from pyscotch import doctor

        expected = f"pyscotch scotch build {sb.latest_version()} "
        assert expected in doctor._scotch_install_hint(False)
        assert expected in doctor._scotch_install_hint(True)


class TestSourceTreeManagement:
    """The submodule-copy machinery: builds never touch the pristine submodule;
    they compile a disposable, quickfix-patched copy prepared by the same
    Python patch code `pyscotch scotch build` uses on tarballs."""

    SUBMODULE = Path(__file__).resolve().parents[2] / "external" / "scotch"

    def _submodule_or_skip(self):
        if not (self.SUBMODULE / "src" / "Makefile").is_file():
            pytest.skip("scotch submodule not initialized")
        return self.SUBMODULE

    def test_detect_version_matches_catalog(self):
        """EQUIVALENCE GUARD: the submodule's version must be in the curated
        catalog (_KNOWN_VERSIONS) — a submodule bump that outruns the catalog
        is exactly how the 7.0.12 wheel build broke. Bump the catalog (sha256
        + patches) together with the submodule."""
        sub = self._submodule_or_skip()
        version = sb.detect_source_version(sub)
        assert version in sb._KNOWN_VERSIONS, (
            f"submodule is Scotch {version}, which is not in the catalog: add "
            "its sha256 (and quickfix patches if needed) to scotch_build.py"
        )

    def test_detect_version_rejects_non_tree(self, tmp_path):
        with pytest.raises(sb.BuildError, match="Not a Scotch source tree"):
            sb.detect_source_version(tmp_path)

    def test_prepare_patches_copy_and_leaves_source_pristine(self, tmp_path, capsys):
        sub = self._submodule_or_skip()
        version = sb.detect_source_version(sub)
        if not sb.patches_for(version):
            pytest.skip(f"Scotch {version} needs no quickfixes; nothing to observe")

        dest = tmp_path / "copy"
        sb.prepare_source_tree(dest, source=sub)
        copy_header = (dest / "src" / "libscotch" / "module.h").read_text()
        sub_header = (sub / "src" / "libscotch" / "module.h").read_text()
        assert "SCOTCH_meshBuildElem" in copy_header, "copy was not patched"
        assert "SCOTCH_meshBuildElem" not in sub_header, (
            "the pristine submodule was modified — prepare must never touch it"
        )

        # Second prepare: stamp fast-path, no re-copy.
        capsys.readouterr()
        sb.prepare_source_tree(dest, source=sub)
        assert "up to date" in capsys.readouterr().out

        # Direct re-patch of the copy: idempotent, detected as applied.
        capsys.readouterr()
        sb.apply_patches(dest)
        assert "already applied" in capsys.readouterr().out


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

    def test_preflight_patch_check_only_when_needed(self):
        assert not any("patch" in c.name for c in sb.preflight(False, need_patch=False))
        assert any("patch" in c.name for c in sb.preflight(False, need_patch=True))


class TestQuickfixPatches:
    def test_catalog_targets_7012_not_7011(self):
        assert sb.patches_for("7.0.12"), "expected a bundled quickfix for 7.0.12"
        assert sb.patches_for("7.0.11") == []

    def test_bundled_patch_files_exist(self):
        # Every patch named in the manifest must actually ship in the package.
        for version, patches in sb._PATCHES.items():
            for fname, _reason in patches:
                assert (sb._patches_dir() / fname).is_file(), f"{version}: {fname} missing"

    def test_patch_records_roundtrip(self, tmp_home):
        _make_build(tmp_home, "7.0.12-64-seq")
        assert store.read_patches("7.0.12-64-seq") == []
        store.write_patches("7.0.12-64-seq", ["a.patch", "b.patch"])
        assert store.read_patches("7.0.12-64-seq") == ["a.patch", "b.patch"]

    def test_cmd_patches_runs(self, capsys):
        rc = sb.cmd_patches(object())
        out = capsys.readouterr().out
        assert rc == 0
        assert "7.0.12" in out and "--pristine" in out


class TestStrictBuildFlags:
    """The build must force the implicit-declaration warning to an error so the
    7.0.12 rename-table regression fails at compile-time on *every* compiler,
    not just GCC >= 14 (which errors by default)."""

    def test_base_cflags_error_on_implicit_decl(self):
        assert "-Werror=implicit-function-declaration" in sb._BASE_CFLAGS

    def test_makefile_inc_carries_strict_flag(self):
        assert "-Werror=implicit-function-declaration" in sb._makefile_inc("gcc", "mpicc")
