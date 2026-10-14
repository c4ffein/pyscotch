"""The upstream report generator (scripts/gen_upstream_report.py): data hygiene and HTML safety.

No browser is needed: these cover `ingest` and the HTML/email rendering, not the PDF step."""

import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("jinja2")

_SPEC = importlib.util.spec_from_file_location(
    "gen_upstream_report", Path(__file__).resolve().parents[2] / "scripts" / "gen_upstream_report.py"
)
gur = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gur)

REVIEW_TITLE = "REVIEW'S OWN TITLE, MUST NEVER SURVIVE"


def _finding(fid="COR-01", status="fixed-in-7.0.17", evidence="plain", **kw):
    return {
        "id": fid,
        "title": REVIEW_TITLE,
        "claimed_severity": "High",
        "status": status,
        "method": "reproduced",
        "location_7_0_17": "src/libscotch/x.c:1",
        "evidence": evidence,
        "upstream_change": "",
        "review_accuracy": "accurate",
        "fix_options": [
            {"label": "A (preferred)", "summary": "s", "patch_sketch": "", "tradeoffs": "", "preferred": True}
        ],
        "notes": "",
        **kw,
    }


@pytest.fixture
def data_dir(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "COR.json").write_text(
        json.dumps(
            [
                _finding(
                    evidence="ran /tmp/claude-1000/-home-x/abc/scratchpad/work/COR/t in /home/dev/workspace/pyscotch/x"
                )
            ]
        )
    )
    (src / "COR.enrich.json").write_text(
        json.dumps([{"id": "COR-01", "our_title": "Our own words", "needs": "", "needs_note": ""}])
    )
    (src / "COR.new.json").write_text(
        json.dumps(
            [
                {
                    "local_id": "PS-COR-1",
                    "our_title": "New one",
                    "severity": "low",
                    "status": "still-present",
                    "method": "source-read",
                    "location_7_0_17": "a.c:2",
                    "evidence": "e",
                    "related_review_ids": [],
                    "fix_options": [],
                }
            ]
        )
    )
    dest = tmp_path / "data"
    gur.ingest("7.0.17", src, dest)
    return dest


def test_ingest_drops_the_review_title_and_keeps_ours(data_dir):
    text = (data_dir / "findings.json").read_text()
    assert REVIEW_TITLE not in text
    f = json.loads(text)["findings"][0]
    assert f["our_title"] == "Our own words"
    assert "title" not in f


def test_ingest_scrubs_local_paths_and_normalises_status_and_labels(data_dir):
    d = json.loads((data_dir / "findings.json").read_text())
    f = d["findings"][0]
    assert "/tmp/claude" not in f["evidence"] and "/home/dev" not in f["evidence"]
    assert f["status"] == "fixed"  # "fixed-in-7.0.17" is canonicalised
    assert f["fix_options"][0]["label"] == "A"  # the duplicated "(preferred)" is dropped
    assert d["new"][0]["local_id"] == "PS-COR-1"


def test_title_missing_from_enrichment_is_none_not_the_review_title(tmp_path):
    src = tmp_path / "s"
    src.mkdir()
    (src / "GRA.json").write_text(json.dumps([_finding("GRA-01")]))
    gur.ingest("7.0.17", src, tmp_path / "d")
    assert json.loads((tmp_path / "d" / "findings.json").read_text())["findings"][0]["our_title"] is None


def test_html_escapes_evidence(data_dir):
    """Regression: select_autoescape(["html"]) does not match 'report.html.j2', so raw '<input ...>' from a
    finding's evidence became a real tag (and crashed the PDF renderer)."""
    d = json.loads((data_dir / "findings.json").read_text())
    d["findings"][0]["evidence"] = (
        "usage: [<input pattern header file> [<output header file>]] <script>alert(1)</script>"
    )
    (data_dir / "findings.json").write_text(json.dumps(d))
    gur.build(data_dir, want_pdf=False)
    html = (data_dir / "out" / "report.html").read_text()
    assert "<input pattern header file>" not in html and "<script>alert(1)" not in html
    assert "&lt;input pattern header file&gt;" in html


def test_stylesheets_are_not_escaped(data_dir):
    gur.build(data_dir, want_pdf=False)
    html = (data_dir / "out" / "report.html").read_text()
    assert "&#39;Inter&#39;" not in html and "font-family:'Inter'" in html


def test_pdf_source_has_no_font_face_and_email_names_the_credit(data_dir):
    gur.build(data_dir, want_pdf=False)
    out = data_dir / "out"
    assert "@font-face" not in (out / ".report-pdf-src.html").read_text()
    email = (out / "email.txt").read_text()
    assert email.startswith("DRAFT") and "Robert Perry" in email


def test_trunc_cuts_at_word_boundary():
    assert gur.trunc("alpha beta gamma", 12) == "alpha beta …"
    assert gur.trunc("short", 50) == "short"


def test_index_lists_every_finding_and_every_link_resolves(data_dir):
    import re

    gur.build(data_dir, want_pdf=False)
    html = (data_dir / "out" / "report.html").read_text()
    ids = set(re.findall(r'id="([^"]+)"', html))
    links = re.findall(r'href="#([^"]+)"', html)
    assert not [t for t in links if t not in ids], "dangling anchors"
    index = html[html.index('id="index"') :]
    index = index[: index.index("<h2", 10)]
    assert 'href="#COR-01"' in index and 'href="#PS-COR-1"' in index  # every finding, incl. our own, is indexed
    assert "report-full" not in html  # one document now


def test_patch_sketches_are_collapsible(data_dir):
    d = json.loads((data_dir / "findings.json").read_text())
    d["findings"][0]["fix_options"][0]["patch_sketch"] = "if (p != NULL) free (p);"
    (data_dir / "findings.json").write_text(json.dumps(d))
    gur.build(data_dir, want_pdf=False)
    assert (
        "<details><summary>patch sketch</summary><pre>if (p != NULL) free (p);</pre></details>"
        in (data_dir / "out" / "report.html").read_text()
    )


def test_build_refuses_findings_without_our_own_title(tmp_path):
    src = tmp_path / "s"
    src.mkdir()
    (src / "GRA.json").write_text(json.dumps([_finding("GRA-01")]))
    gur.ingest("7.0.17", src, tmp_path / "d")
    with pytest.raises(SystemExit, match="no title in our own words"):
        gur.build(tmp_path / "d", want_pdf=False)
    gur.build(tmp_path / "d", want_pdf=False, allow_pending=True)  # an explicit draft is still possible


# --- merge-audit: overlay, duplicate patches, combined series ---------------------------------------------
def _git(*args, cwd):
    import subprocess

    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def _repo_with_patches(tmp_path, conflicting=False):
    """A tiny 'scotch' repo tagged v7.0.17 and a work dir with two groups of patches.

    G01/0001 and G02/0001 are the same fix (identical content); G02/0002 touches another line, so the series applies
    only with a 3-way merge after G01's patch; with `conflicting`, G02/0002 instead rewrites G01's line differently."""
    import subprocess

    repo = tmp_path / "scotch"
    repo.mkdir()
    g = ["git", "-c", "init.defaultBranch=main"]
    subprocess.run(g + ["init", "-q"], cwd=repo, check=True)
    _git("config", "user.name", "t", cwd=repo)
    _git("config", "user.email", "t@t", cwd=repo)
    src = repo / "src"
    src.mkdir()
    (src / "a.c").write_text("line1\nline2\nline3\nline4\nline5\n")
    _git("add", ".", cwd=repo)
    _git("commit", "-q", "-m", "base", cwd=repo)
    _git("tag", "v7.0.17", cwd=repo)
    work = tmp_path / "work"

    def group(name, edits, ids):
        _git("checkout", "-q", "-b", name, "v7.0.17", cwd=repo)
        for n, (text, subject) in enumerate(edits, 1):
            (src / "a.c").write_text(text)
            _git("commit", "-q", "-am", subject, cwd=repo)
        out = work / name / "patches"
        out.mkdir(parents=True)
        _git("format-patch", "-q", "-o", str(out), "v7.0.17", cwd=repo)
        files = sorted(str(p) for p in out.glob("*.patch"))
        (work / name / "audit.json").write_text(
            json.dumps(
                [
                    {
                        "id": i,
                        "our_title": "t",
                        "status": "still-present",
                        "method": "ran",
                        "severity": "low",
                        "fix_options": [],
                        "patch_files": [files[k]],
                    }
                    for k, i in enumerate(ids)
                ]
            )
        )
        (work / name / "extra.json").write_text(
            json.dumps(
                [
                    {
                        "local_id": f"PS2-{name}-1",
                        "our_title": "x",
                        "severity": "info",
                        "status": "still-present",
                        "method": "source-read",
                        "fix_options": [],
                        "patch_files": [],
                    }
                ]
            )
        )
        _git("checkout", "-q", "v7.0.17", cwd=repo)

    fix1 = "LINE1\nline2\nline3\nline4\nline5\n"
    group("G01", [(fix1, "Bugfix: the first line")], ["COR-01"])
    if conflicting:  # G02 rewrites the line G01 changed, from the pristine base: no 3-way merge can resolve that
        group("G02", [("other1\nline2\nline3\nline4\nline5\n", "Bugfix: the other line")], ["COR-02"])
    else:
        second = "LINE1\nline2\nline3\nline4\nLINE5 differently\n"
        group("G02", [(fix1, "Bugfix: the first line"), (second, "Bugfix: the other line")], ["COR-02", "PS-COR-1"])
    return repo, work


def _ingest_two(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "COR.json").write_text(json.dumps([_finding("COR-01"), _finding("COR-02"), _finding("COR-03")]))
    (src / "COR.enrich.json").write_text(
        json.dumps([{"id": i, "our_title": "w"} for i in ("COR-01", "COR-02", "COR-03")])
    )
    (src / "COR.new.json").write_text(
        json.dumps(
            [
                {
                    "local_id": "PS-COR-1",
                    "our_title": "n",
                    "severity": "low",
                    "status": "still-present",
                    "method": "source-read",
                    "location_7_0_17": "a.c:2",
                    "evidence": "e",
                    "related_review_ids": [],
                    "fix_options": [],
                }
            ]
        )
    )
    dest = tmp_path / "data"
    gur.ingest("7.0.17", src, dest)
    return dest


def test_merge_audit_flags_identical_patches_and_exports_one_combined_series(tmp_path, capsys):
    repo, work = _repo_with_patches(tmp_path)
    dest = _ingest_two(tmp_path)
    gur.merge_audit(work, dest, check_apply=repo)
    data = json.loads((dest / "findings.json").read_text())
    series = data["series"]
    assert [s["file"].split("/")[1] for s in series] == ["G01", "G02", "G02"]
    assert "duplicate_of" not in series[0] and series[1]["duplicate_of"] == series[0]["file"]
    assert series[0]["ids"] == ["COR-01", "COR-02"], "the kept patch carries the ids of its duplicate"
    assert data["combined"]["count"] == 2 and data["combined"]["plain_apply"] and not data["combined"]["conflicts"]
    assert sorted(p.name for p in (dest / "series").glob("*.patch")) == [
        series[0]["combined_file"].split("/")[1],
        series[2]["combined_file"].split("/")[1],
    ]
    assert "combined_file" not in series[1]
    out = capsys.readouterr().out
    assert "2 of 2 distinct patches apply" in out and "plain `git am` on a fresh clone: OK" in out
    assert "1 not yet" in out and "COR-03" in out, "PS2 extras are not counted as unaudited items"
    by_id = {f["id"]: f for f in data["findings"]}
    assert by_id["COR-01"]["group"] == "G01" and by_id["COR-02"]["status"] == "still-present"
    assert {n["local_id"] for n in data["new"]} == {"PS-COR-1", "PS2-G01-1", "PS2-G02-1"}
    assert next(n for n in data["new"] if n["local_id"] == "PS-COR-1")["group"] == "G02", (
        "first-pass PS-* items get audited too"
    )


def test_merge_audit_reports_a_real_conflict_and_exports_nothing(tmp_path, capsys):
    repo, work = _repo_with_patches(tmp_path, conflicting=True)
    dest = _ingest_two(tmp_path)
    gur.merge_audit(work, dest, check_apply=repo)
    data = json.loads((dest / "findings.json").read_text())
    assert data["combined"]["count"] == 0 and not data["combined"]["plain_apply"]
    assert [c["file"] for c in data["combined"]["conflicts"]] == [data["series"][1]["file"]]
    assert data["combined"]["conflicts"][0]["on"] == ["src/a.c"]
    assert not (dest / "series").exists()
    assert "DOES NOT APPLY" in capsys.readouterr().out


def test_merge_audit_is_idempotent(tmp_path):
    repo, work = _repo_with_patches(tmp_path)
    dest = _ingest_two(tmp_path)
    gur.merge_audit(work, dest, check_apply=repo)
    first = json.loads((dest / "findings.json").read_text())
    gur.merge_audit(work, dest, check_apply=repo)
    second = json.loads((dest / "findings.json").read_text())
    assert first == second


def test_patch_subject_unfolds_continuation_lines(tmp_path):
    p = tmp_path / "0001-x.patch"
    p.write_text(
        "From abc\nSubject: [PATCH 3/9] Bugfix: a very long subject that git\n folded onto a second line\n\nbody\n"
    )
    assert gur._patch_subject(p) == "Bugfix: a very long subject that git folded onto a second line"


def test_build_renders_the_combined_series_and_marks_duplicates(tmp_path):
    repo, work = _repo_with_patches(tmp_path)
    dest = _ingest_two(tmp_path)
    gur.merge_audit(work, dest, check_apply=repo)
    gur.build(dest, want_pdf=False, allow_pending=True, internal=False)
    html = (dest / "out" / "report.html").read_text()
    assert "2 distinct commits" in html and "one series" in html and 'href="series/' in html
    assert "same fix as" in html, "the duplicate row says which patch it repeats"
    email = (dest / "out" / "email.txt").read_text()
    assert "2 of the fixes are attached" in email


def test_merge_audit_order_file_puts_named_groups_first_and_is_recorded(tmp_path):
    repo, work = _repo_with_patches(tmp_path)
    dest = _ingest_two(tmp_path)
    order = tmp_path / "order.txt"
    order.write_text("# apply G02 before G01\nG02\n")
    gur.merge_audit(work, dest, check_apply=repo, order_file=order)
    data = json.loads((dest / "findings.json").read_text())
    assert data["audited_groups"] == ["G02", "G01"]
    assert [s["file"].split("/")[1] for s in data["series"]] == ["G02", "G02", "G01"]
    assert data["series"][2]["duplicate_of"] == data["series"][0]["file"], "the kept copy is now G02's"
    assert data["combined"]["count"] == 2 and data["combined"]["plain_apply"]
    order.write_text("G99\n")
    with pytest.raises(SystemExit):
        gur.merge_audit(work, dest, check_apply=repo, order_file=order)


def test_merge_audit_exports_groups_per_version_and_reproducers_outside_it(tmp_path):
    repo, work = _repo_with_patches(tmp_path)
    for g, fid in (("G01", "COR-01"), ("G02", "COR-02")):
        (work / g / "SUMMARY.md").write_text(f"# {g}\n")
        r = work / g / "repro"
        (r / fid).mkdir(parents=True)
        (r / fid / "README").write_text("run ../common/drv\n")
        (r / fid / "drv.c").write_text("int main(void) { return 0; }\n")
        (r / fid / "core.1234").write_bytes(b"\0" * 64)  # a core dump: never exported
        (r / "common").mkdir()
        (r / "common" / "fi.h").write_text("/* shared harness */\n")
    dest = _ingest_two(tmp_path)
    repro_root = tmp_path / "repro"
    gur.merge_audit(work, dest, repro_root=repro_root)
    data = json.loads((dest / "findings.json").read_text())
    assert sorted(p.name for p in (dest / "groups" / "G01").iterdir()) == ["SUMMARY.md", "audit.json", "extra.json"]
    assert (repro_root / "G01" / "COR-01" / "drv.c").is_file() and (repro_root / "G01" / "common" / "fi.h").is_file()
    assert not (repro_root / "G01" / "COR-01" / "core.1234").exists()
    assert not (dest / "repro").exists() and not (dest / "audit").exists(), "reproducers never live in a version dir"
    by_id = {f["id"]: f for f in data["findings"]}
    assert by_id["COR-01"]["repro"] == "G01/COR-01" and by_id["COR-02"]["repro"] == "G02/COR-02"
    assert "repro" not in by_id["COR-03"]


def test_merge_audit_keeps_one_finding_per_id_when_several_groups_record_it(tmp_path):
    repo, work = _repo_with_patches(tmp_path)
    # G02 records the same new defect as G01 (forwarded leads do that) and re-audits G01's lead
    extra = json.loads((work / "G02" / "extra.json").read_text())
    extra[0]["local_id"] = "PS2-G01-1"
    extra[0]["our_title"] = "G02's view"
    (work / "G02" / "extra.json").write_text(json.dumps(extra))
    audit = json.loads((work / "G02" / "audit.json").read_text())
    second = dict(audit[0], id="COR-01", our_title="G02's view of COR-01")
    (work / "G02" / "audit.json").write_text(json.dumps(audit + [second]))
    dest = _ingest_two(tmp_path)
    gur.merge_audit(work, dest)
    data = json.loads((dest / "findings.json").read_text())
    ids = [f.get("id") or f.get("local_id") for f in data["findings"] + data["new"]]
    assert len(ids) == len(set(ids)), "one entry per id"
    new = {n["local_id"]: n for n in data["new"]}
    assert new["PS2-G01-1"]["group"] == "G01" and [v["group"] for v in new["PS2-G01-1"]["also"]] == ["G02"]
    cor01 = next(f for f in data["findings"] if f["id"] == "COR-01")
    assert cor01["group"] == "G01" and cor01["also"][0]["our_title"] == "G02's view of COR-01"
    assert set(cor01["also"][0]["patch_files"]) <= set(cor01["patch_files"]), "patches of every view are kept"
