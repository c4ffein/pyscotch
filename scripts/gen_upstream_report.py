#!/usr/bin/env python3
"""Per-Scotch-version status report for the Scotch maintainers (HTML + PDF + email draft).

    gen_upstream_report.py ingest      --version 7.0.17 --from DIR --to DATA_DIR
    gen_upstream_report.py merge-audit --from WORKROOT --to DATA_DIR [--check-apply SCOTCH_GIT] [--order FILE]
                                       [--repro-root upstream/repro]
    gen_upstream_report.py build       --data DATA_DIR [--pdf] [--internal]

DATA_DIR (upstream/reports/<version>/, committed; its out/ is gitignored) holds what depends on that release
(the reproducer kits, which do not, go to upstream/repro/<group>/ with --repro-root):
  findings.json   the merged, review-text-free data ("ingest" writes it)
  meta.json       review credit, previous version, highlights, sender (hand-edited)
and "build" writes DATA_DIR/out/{report.html, report.pdf, email.txt}.

`ingest` merges the per-area verification files (<PREFIX>.json + <PREFIX>.enrich.json +
<PREFIX>.new.json) and deliberately DROPS the third party review's own titles: we cite its
identifiers, never its text. Absolute scratch paths are scrubbed from evidence.

`merge-audit` layers the second, per-file-group pass (WORKROOT/<GROUP>/{audit,extra}.json) over an
ingested findings.json: status / method / severity / evidence are replaced by the audited ones, the
first pass is kept under "first_pass" for traceability (never rendered for the maintainer), and the
recommended commits (git format-patch) and the alternative diffs are copied under DATA_DIR/patches/
and DATA_DIR/alt/ with relative references. `--check-apply` applies every group's series in order on a
fresh clone of the given Scotch git to prove they do not collide.

The PDF needs Playwright + Chromium (uv pip install playwright && playwright install chromium);
on a box without Chromium's system libraries, point CHROMIUM_LIBS at a directory holding them.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO / "upstream" / "report-templates"

AREAS = {  # prefix -> (display name, order)
    "COR": "Core utilities, strategy parser, target architectures",
    "GRA": "Sequential graphs, ordering, k-way mapping",
    "SEP": "Bipartitioning, separators, meshes",
    "API": "Public C API and Fortran wrappers",
    "DGR": "Distributed graph and mesh core (PT-Scotch)",
    "DMO": "Distributed mapping and ordering (PT-Scotch)",
    "CLI": "Command-line tools, esMUMPS, METIS shim",
    "BLD": "Build system, tests, CI",
}
SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
LABELS = {
    "fixed": "fixed upstream",
    "partially-fixed": "partially fixed",
    "still-present": "still present",
    "not-a-bug": "not a bug",
    "inconclusive": "inconclusive",
}
NEEDS_LABELS = {
    "alloc-injection": "needs forced allocation failures",
    "mpi-fault": "needs a failing MPI rank",
    "other-platform": "needs a platform we do not have",
    "64bit-build": "needs a 64-bit INT build",
    "debug-build": "needs a SCOTCH_DEBUG build",
    "external-dependency": "needs a tool or dependency not available here",
    "none-found": "source read was conclusive; nothing to run",
}
_SCRUB = [
    (re.compile(r"/tmp/claude-[^\s'\":)]*?/scratchpad/"), ""),
    (re.compile(r"/home/dev/workspace/pyscotch/?"), ""),
]


def scrub(text):
    if isinstance(text, str):
        for rx, rep in _SCRUB:
            text = rx.sub(rep, text)
    return text


def scrub_deep(obj):
    if isinstance(obj, dict):
        return {k: scrub_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_deep(v) for v in obj]
    return scrub(obj)


def clean_options(options):
    """The `preferred` flag carries the preference; drop a literal "(preferred)" some labels also had."""
    return [{**o, "label": re.sub(r"\s*\(preferred\)\s*", " ", o.get("label", "")).strip()} for o in options]


def trunc(text, n):
    """Cut at a word boundary, with an ellipsis, never mid-word."""
    text = text or ""
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",;:") + " …"


def canon_status(s):
    return "fixed" if s.startswith("fixed") else s


# --- ingest ---------------------------------------------------------------
def ingest(version, src, dest):
    src, dest = Path(src), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    findings, new, missing = [], [], []
    for prefix in AREAS:
        base = src / f"{prefix}.json"
        if not base.exists():
            missing.append(prefix)
            continue
        enrich = {}
        ep = src / f"{prefix}.enrich.json"
        if ep.exists():
            enrich = {e["id"]: e for e in json.load(open(ep))}
        for f in json.load(open(base)):
            e = enrich.get(f["id"], {})
            findings.append(
                scrub_deep(
                    {
                        "id": f["id"],
                        "area": prefix,
                        # the review's own title is intentionally NOT carried over
                        "our_title": e.get("our_title") or None,
                        "claimed_severity": f["claimed_severity"].lower(),
                        "status": canon_status(f["status"]),
                        "method": f["method"],
                        "needs": e.get("needs", ""),
                        "needs_note": e.get("needs_note", ""),
                        "location": f.get("location_7_0_17", ""),
                        "evidence": f.get("evidence", ""),
                        "upstream_change": f.get("upstream_change", ""),
                        "review_accuracy": f.get("review_accuracy", ""),
                        "fix_options": clean_options(f.get("fix_options", [])),
                        "notes": f.get("notes", ""),
                        "history": {"reported": "reported", version: canon_status(f["status"])},
                    }
                )
            )
        np_ = src / f"{prefix}.new.json"
        if np_.exists():
            for n in json.load(open(np_)):
                n["area"] = prefix
                n["status"] = canon_status(n.get("status", "still-present"))
                n["fix_options"] = clean_options(n.get("fix_options", []))
                new.append(scrub_deep(n))
    out = {"scotch_version": version, "findings": findings, "new": new}
    json.dump(out, open(dest / "findings.json", "w"), indent=1, ensure_ascii=False)
    untitled = [f["id"] for f in findings if not f["our_title"]]
    print(f"{len(findings)} findings, {len(new)} new defects -> {dest / 'findings.json'}")
    if missing:
        print("areas with no verification file:", ", ".join(missing))
    if untitled:
        more = " ..." if len(untitled) > 6 else ""
        print(f"{len(untitled)} findings have no title in our own words yet: {', '.join(untitled[:6])}{more}")
    meta = dest / "meta.json"
    if not meta.exists():
        json.dump(
            {
                "review": {"author": "Robert Perry", "date": "2026-10-07"},
                "previous": {"version": "7.0.16", "commit": "b748bc4"},
                "sender": "[your name]",
                "verifier": "PyScotch, with automated assistance",
                "highlights": [],
            },
            open(meta, "w"),
            indent=1,
        )
        print("wrote a starter", meta, "- edit it")


# --- merge-audit ----------------------------------------------------------
RAN_METHODS = ("ran", "partly-run", "reproduced", "both")  # old (first pass) and new (audit) vocabularies


def is_run(method):
    return method in RAN_METHODS


def _rel_copy(path, data_dir, sub, group):
    """Copy one patch/diff file from the agents' work dir into DATA_DIR/<sub>/<group>/; return the relative path."""
    src = Path(path)
    if not src.is_file():
        return None
    dest = data_dir / sub / group / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return f"{sub}/{group}/{src.name}"


def _patch_subject(path):
    """The commit subject of a `git format-patch` file, unfolded (long subjects continue on indented lines)."""
    lines = Path(path).read_text(errors="replace").split("\n")
    for i, line in enumerate(lines):
        if line.startswith("Subject:"):
            subject = re.sub(r"^Subject:\s*(\[PATCH[^\]]*\]\s*)?", "", line).strip()
            for cont in lines[i + 1 :]:
                if not cont.startswith(" "):
                    break
                subject += " " + cont.strip()
            return subject
    return ""


def _audited(f, a, data_dir, group):
    """Overlay one audit entry `a` onto the ingested finding `f` (in place)."""
    if "first_pass" not in f:  # keep the first pass's own claims when merge-audit is re-run on overlaid data
        f["first_pass"] = {
            "status": f["status"],
            "method": f["method"],
            "our_title": f.get("our_title"),
            "preferred_fix": next((o["label"] for o in f.get("fix_options", []) if o.get("preferred")), ""),
        }
    f["status"] = canon_status(a["status"])
    f["method"] = a["method"]
    f["our_title"] = a.get("our_title") or f.get("our_title")
    f["severity"] = a.get("severity", "")
    f["severity_note"] = a.get("severity_note", "")
    f["ran"] = a.get("ran", "")
    f["read_only"] = a.get("read_only", "")
    f["why_not_run"] = a.get("why_not_run", "")
    f["location"] = a.get("location_7_0_17") or f.get("location", "")
    f["evidence"] = a.get("evidence", "")
    f["upstream_change"] = a.get("upstream_change", "")
    f["review_accuracy"] = a.get("review_accuracy", "")
    f["first_pass_critique"] = a.get("first_pass_critique", "")
    f["extra_instances"] = a.get("extra_instances", [])
    opts = []
    for o in a.get("fix_options", []):
        o = dict(o)
        if o.get("diff_file"):
            sub = "patches" if "/patches/" in o["diff_file"] else "alt"
            o["diff_file"] = _rel_copy(o["diff_file"], data_dir, sub, group) or ""
        opts.append(o)
    f["fix_options"] = clean_options(opts)
    f["patch_files"] = [p for p in (_rel_copy(p, data_dir, "patches", group) for p in a.get("patch_files", [])) if p]
    f["cleanup_done"] = a.get("cleanup_done", "")
    f["test_added"] = a.get("test_added", "")
    f["docs_updated"] = a.get("docs_updated", "")
    f["needs"] = a.get("needs", "")
    f["needs_note"] = a.get("needs_note", "")
    f["notes"] = a.get("notes", "")
    f["group"] = group
    return f


def group_order(src, order_file=None):
    """The groups to merge, in apply order: those named in `order_file` (one per line, # comments) first, in that
    order, then the others alphabetically. Order matters: a group whose patches were made on top of other groups'
    series must come after them."""
    found = sorted(p.parent.name for p in src.glob("G*/audit.json"))
    wanted = []
    if order_file:
        for line in Path(order_file).read_text().split("\n"):
            name = line.split("#", 1)[0].strip()
            if name and name not in wanted:
                wanted.append(name)
    missing = [g for g in wanted if g not in found]
    if missing:
        raise SystemExit(f"--order names groups with no audit.json: {', '.join(missing)}")
    return wanted + [g for g in found if g not in wanted]


REPRO_KEEP = re.compile(
    r"\.(c|h|sh|py|f90|txt|md|tgt|grf|msh|map|ord|json|mtx|chac|rsa|xyz|adm|pue|diff|patch|cmake|in)$|^README|^Makefile",
    re.I,
)


def _view(f, group):
    """A secondary group's view of a finding another group already owns (same id, recorded twice)."""
    keep = (
        "our_title",
        "status",
        "method",
        "severity",
        "evidence",
        "ran",
        "notes",
        "fix_options",
        "patch_files",
        "test_added",
    )
    return {"group": group, **{k: f[k] for k in keep if f.get(k)}}


def _absorb(owner, other, group):
    """Merge `other` (same id, audited by `group`) into `owner`: patches are unioned, the rest kept as a view."""
    owner["patch_files"] = owner.get("patch_files", []) + [
        p for p in other.get("patch_files", []) if p not in owner.get("patch_files", [])
    ]
    owner.setdefault("also", []).append(_view(other, group))


def export_group(src, dest, group, repro_root=None):
    """Copy a group's summary and raw audit into DATA_DIR/groups/<group>/, and its source-level reproducer kit
    (sources, inputs, logs; no binaries or core dumps) into REPRO_ROOT/<group>/, which lives outside any version."""
    import shutil

    gd = dest / "groups" / group
    gd.mkdir(parents=True, exist_ok=True)
    for name in ("SUMMARY.md", "audit.json", "extra.json"):
        if (src / group / name).is_file():
            shutil.copy(src / group / name, gd / name)
    rep = src / group / "repro"
    if repro_root is None or not rep.is_dir():
        return
    out = Path(repro_root) / group
    shutil.rmtree(out, ignore_errors=True)
    for f in rep.rglob("*"):
        if f.is_file() and REPRO_KEEP.search(f.name) and f.stat().st_size < 2_000_000:
            t = out / f.relative_to(rep)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, t)


def merge_audit(src, dest, check_apply=None, order_file=None, repro_root=None):
    src, dest = Path(src), Path(dest)
    data = json.load(open(dest / "findings.json"))
    ver = data["scotch_version"]
    by_id = {f["id"]: f for f in data["findings"]}
    by_id.update({n["local_id"]: n for n in data["new"]})
    for f in by_id.values():  # recomputed below: re-running merge-audit must not accumulate them
        f.pop("also", None)
        f.pop("repro", None)
    candidates = [i for i, f in by_id.items() if not f.get("group")]  # PS2-* extras are never audit targets
    groups = group_order(src, order_file)
    seen, extra, series = set(), [], []
    for group in groups:
        export_group(src, dest, group, repro_root)
        for a in json.load(open(src / group / "audit.json")):
            f = by_id.get(a["id"])
            if f is None:
                print(f"{group}: audit entry {a['id']} matches no ingested finding; skipped")
                continue
            if a["id"] in seen:  # a second group audited the same lead: keep the first as owner, attach this view
                import copy

                other = copy.deepcopy(f)
                _audited(other, a, dest, group)
                _absorb(f, other, group)
                continue
            if "local_id" in f:  # a PS-* defect from the first pass: same overlay, keyed differently
                f.setdefault("history", {"reported": "reported", ver: f["status"]})
                f.setdefault("fix_options", [])
            _audited(f, a, dest, group)
            f["history"][ver] = f["status"]
            seen.add(a["id"])
        ep = src / group / "extra.json"
        if ep.exists():
            for n in json.load(open(ep)):
                n = dict(n)
                n["group"] = group
                n["status"] = canon_status(n.get("status", "still-present"))
                n["related_review_ids"] = n.get("related_ids", n.get("related_review_ids", []))
                opts = []
                for o in n.get("fix_options", []):
                    o = dict(o)
                    if o.get("diff_file"):
                        sub = "patches" if "/patches/" in o["diff_file"] else "alt"
                        o["diff_file"] = _rel_copy(o["diff_file"], dest, sub, group) or ""
                    opts.append(o)
                n["fix_options"] = clean_options(opts)
                n["patch_files"] = [
                    p for p in (_rel_copy(p, dest, "patches", group) for p in n.get("patch_files", [])) if p
                ]
                owner = next((e for e in extra if e["local_id"] == n["local_id"]), None)
                if owner is not None:  # the same new defect recorded by several groups: one finding, several views
                    _absorb(owner, n, group)
                else:
                    extra.append(n)
        for p in sorted((src / group / "patches").glob("*.patch")):
            rel = _rel_copy(p, dest, "patches", group)
            ids = sorted(i for i, f in by_id.items() if rel in f.get("patch_files", []))
            ids += sorted(n["local_id"] for n in extra if rel in n.get("patch_files", []))
            series.append({"group": group, "file": rel, "subject": _patch_subject(p), "ids": ids})
    data["new"] = [n for n in data["new"] if n["local_id"] not in {e["local_id"] for e in extra}] + extra
    if repro_root is not None:  # point every finding (and every secondary view) at its reproducer folder
        for f in data["findings"] + data["new"]:
            fid_ = f.get("id") or f.get("local_id")
            for v in [f] + f.get("also", []):
                g = v.get("group")
                if g and (Path(repro_root) / g / fid_).is_dir():
                    v["repro"] = f"{g}/{fid_}"
    data["findings"] = [scrub_deep(f) for f in data["findings"]]
    data["new"] = [scrub_deep(n) for n in data["new"]]
    data["series"] = mark_duplicate_patches(dest, series)
    data["audited_groups"] = groups
    data.pop("combined", None)
    if check_apply:
        data["combined"] = combine_series(dest, data["series"], check_apply, data["scotch_version"])
    json.dump(data, open(dest / "findings.json", "w"), indent=1, ensure_ascii=False)
    unaudited = [i for i in candidates if i not in seen]
    dups = sum(1 for s in series if s.get("duplicate_of"))
    print(
        f"{len(groups)} groups merged; {len(seen)} items audited, {len(unaudited)} not yet; "
        f"{len(extra)} further defects; {len(series)} patches ({dups} duplicates) -> {dest / 'findings.json'}"
    )
    if unaudited:
        print("not yet audited:", ", ".join(unaudited[:12]), "..." if len(unaudited) > 12 else "")


def patch_id(path):
    """Content hash of a patch (`git patch-id --stable`): identical fixes committed by two groups share it."""
    import subprocess

    out = subprocess.run(
        ["git", "patch-id", "--stable"], input=Path(path).read_text(errors="replace"), capture_output=True, text=True
    ).stdout.split()
    return out[0] if out else ""


def mark_duplicate_patches(dest, series):
    """Flag every patch whose content equals an earlier one in the series (`duplicate_of`), merging the ids."""
    first = {}
    for s in series:
        pid = patch_id(dest / s["file"])
        s.pop("duplicate_of", None)
        if pid and pid in first:
            s["duplicate_of"] = first[pid]["file"]
            first[pid]["ids"] = sorted(set(first[pid]["ids"]) | set(s["ids"]))
        elif pid:
            first[pid] = s
    return series


def _git(*args, cwd=None, check=True, **kw):
    import subprocess

    quiet = ["-c", "advice.detachedHead=false", "-c", "init.defaultBranch=main"]
    return subprocess.run(["git", *quiet, *args], cwd=cwd, capture_output=True, text=True, check=check, **kw)


def _fresh_clone(scotch_git, where, ver):
    _git("clone", "-q", "--shared", str(scotch_git), str(where))
    _git("checkout", "-q", f"v{ver}", cwd=where)
    _git("config", "user.name", "PyScotch", cwd=where)
    _git("config", "user.email", "pyscotch@noreply.invalid", cwd=where)


def combine_series(dest, series, scotch_git, ver):
    """Apply every non-duplicate patch in series order (3-way) on a fresh clone at v<ver>, export the result as ONE
    series under DATA_DIR/series/, and prove that series applies with a plain `git am` on another fresh clone.

    Returns the summary that goes into findings.json["combined"]; prints what does not apply (collisions between
    groups that need a rebase of the later patch)."""
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="series-combine-"))
    out = {"dir": "series", "count": 0, "conflicts": [], "plain_apply": False}
    try:
        work = tmp / "w"
        _fresh_clone(scotch_git, work, ver)
        kept = []
        for s in series:
            s.pop("combined_file", None)
            if s.get("duplicate_of"):
                continue
            r = _git("am", "-q", "-3", str((dest / s["file"]).resolve()), cwd=work, check=False)
            if r.returncode != 0:
                conflict = _git("diff", "--name-only", "--diff-filter=U", cwd=work, check=False).stdout.split()
                _git("am", "--abort", cwd=work, check=False)
                why = next(
                    (ln for ln in reversed((r.stdout + r.stderr).split("\n")) if ln and not ln.startswith("hint:")), ""
                )
                out["conflicts"].append({"file": s["file"], "on": conflict, "why": why})
                continue
            kept.append(s)
        n = len(kept)
        print(f"series apply check: {n} of {n + len(out['conflicts'])} distinct patches apply in sequence on v{ver}")
        for c in out["conflicts"]:
            print("  DOES NOT APPLY:", c["file"], "- conflicts in", ", ".join(c["on"]) or f"(no file: {c['why']})")
        if out["conflicts"]:
            return out
        sdir = dest / "series"
        shutil.rmtree(sdir, ignore_errors=True)
        sdir.mkdir(parents=True)
        _git("format-patch", "-q", "-o", str(sdir.resolve()), f"v{ver}", cwd=work)
        files = sorted(p.name for p in sdir.glob("*.patch"))
        if len(files) != n:
            raise RuntimeError(f"combined series has {len(files)} patches, expected {n}")
        for s, f in zip(kept, files):
            s["combined_file"] = f"series/{f}"
        out["count"] = n
        verify = tmp / "v"
        _fresh_clone(scotch_git, verify, ver)
        r = _git("am", "-q", *[str((sdir / f).resolve()) for f in files], cwd=verify, check=False)
        out["plain_apply"] = r.returncode == 0
        print(
            f"combined series: {n} patches -> {sdir}; plain `git am` on a fresh clone:"
            f" {'OK' if out['plain_apply'] else 'FAILED: ' + r.stderr.strip().split(chr(10))[-1]}"
        )
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- build ----------------------------------------------------------------
def font_files():
    """[(family, weight, bytes)] for the pinned fonts, downloaded once into the user cache and hash-checked."""
    manifest = json.load(open(REPORT_DIR / "fonts.json"))
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "pyscotch-report-fonts"
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for f in manifest["fonts"]:
        path = cache / f["file"]
        if not path.exists():
            data = urllib.request.urlopen(f["url"], timeout=60).read()
            if hashlib.sha256(data).hexdigest() != f["sha256"]:
                sys.exit(f"font checksum mismatch for {f['file']}")
            path.write_bytes(data)
        out.append((f["family"], f["weight"], path.read_bytes()))
    return out


def fonts_css(files):
    """@font-face rules with the fonts embedded as data: URIs (for the HTML report opened in a browser)."""
    return "\n".join(
        f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:normal;"
        f"src:url(data:font/woff2;base64,{base64.b64encode(data).decode()}) format('woff2');}}"
        for fam, w, data in files
    )


def summarise(findings):
    c = {"total": len(findings), "fixed": 0, "partial": 0, "present": 0, "nobug": 0, "open": 0}
    key = {
        "fixed": "fixed",
        "partially-fixed": "partial",
        "still-present": "present",
        "not-a-bug": "nobug",
        "inconclusive": "open",
    }
    run = 0
    for f in findings:
        c[key[f["status"]]] += 1
        run += is_run(f["method"])
    return c, {"run": run, "read": len(findings) - run}


def build(data_dir, want_pdf, allow_pending=False, internal=False):
    from jinja2 import Environment, FileSystemLoader

    data_dir = Path(data_dir)
    data = json.load(open(data_dir / "findings.json"))
    meta = json.load(open(data_dir / "meta.json"))
    ver, findings, new = data["scotch_version"], data["findings"], data.get("new", [])
    untitled = [f["id"] for f in findings if not f.get("our_title")] + [
        n["local_id"] for n in new if not n.get("our_title")
    ]
    if untitled and not allow_pending:
        sys.exit(
            f"{len(untitled)} findings have no title in our own words ({', '.join(untitled[:5])}...): "
            "write them (see <PREFIX>.enrich.json) or pass --allow-pending for a draft"
        )
    areas = []
    for prefix, name in AREAS.items():
        fs = [f for f in findings if f["area"] == prefix]
        if not fs:
            continue
        fs.sort(key=lambda f: (SEV_ORDER.get(f["claimed_severity"], 9), not is_run(f["method"]), f["id"]))
        c, v = summarise(fs)
        areas.append({"prefix": prefix, "name": name, "findings": fs, **c, **v})
    counts, vcount = summarise(findings)
    counts["fixed_high"] = sum(1 for f in findings if f["status"] == "fixed" and f["claimed_severity"] == "high")
    by_sev = lambda f: (SEV_ORDER.get(f["claimed_severity"], 9), not is_run(f["method"]), f["id"])  # noqa: E731
    changed = sorted((f for f in findings if f["status"] in ("fixed", "partially-fixed")), key=by_sev)
    fixfirst = sorted(
        (
            f
            for f in findings
            if f["claimed_severity"] == "high" and f["status"] in ("still-present", "partially-fixed")
        ),
        key=by_sev,
    )
    new.sort(key=lambda f: (SEV_ORDER.get(f.get("severity", "info"), 9), f["local_id"]))
    env = Environment(
        loader=FileSystemLoader(REPORT_DIR), autoescape=True, trim_blocks=True, lstrip_blocks=True
    )  # not select_autoescape: "report.html.j2" ends in .j2
    ctx = {
        "ver": ver,
        "prev": meta["previous"],
        "review": meta["review"],
        "verifier": meta.get("verifier", ""),
        "highlights": meta.get("highlights", []),
        "generated": date.today().isoformat(),
        "areas": areas,
        "counts": counts,
        "vcount": vcount,
        "total": counts["total"],
        "changed": changed,
        "fixfirst": fixfirst,
        "new": new,
        "labels": LABELS,
        "needs_labels": NEEDS_LABELS,
        "fonts_css": fonts_css(font_files()),
        "css": (REPORT_DIR / "report.css").read_text(),
        "sender": meta.get("sender", ""),
        "top": fixfirst[:6],
        "internal": internal,
        "series": data.get("series", []),
        "combined": data.get("combined") or {},
        "distinct": sum(1 for s in data.get("series", []) if not s.get("duplicate_of")),
        "audited": bool(data.get("audited_groups")),
        "patched": sum(1 for f in findings if f.get("patch_files")),
        "patched_new": sum(1 for n in new if n.get("patch_files")),
        "read_patch": lambda rel: (
            (data_dir / rel).read_text(errors="replace") if rel and (data_dir / rel).is_file() else ""
        ),
    }
    out = data_dir / "out"
    out.mkdir(exist_ok=True)
    env.filters["trunc"] = trunc
    tpl = env.get_template("report.html.j2")
    (out / "report.html").write_text(tpl.render(**ctx))
    (out / ".report-pdf-src.html").write_text(tpl.render(**{**ctx, "fonts_css": ""}))
    env_txt = Environment(loader=FileSystemLoader(REPORT_DIR), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    env_txt.filters["trunc"] = trunc
    (out / "email.txt").write_text(env_txt.get_template("email.txt.j2").render(**ctx))
    print("wrote", out / "report.html", out / "email.txt")
    if want_pdf:
        html_to_pdf(out / ".report-pdf-src.html", out / "report.pdf")


_LOAD_FONTS_JS = """async (fonts) => {
  const bad = [];
  for (const [family, weight, b64] of fonts) {
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const face = new FontFace(family, bytes.buffer, {weight: String(weight), style: 'normal'});
    try { await face.load(); document.fonts.add(face); }
    catch (e) { bad.push(family + ' ' + weight + ': ' + e.message); }
  }
  await document.fonts.ready;
  return bad;
}"""


def html_to_pdf(html, pdf):
    """Render with Chromium. Fonts go in through the FontFace API (bytes, no network path): in a box with
    no system fonts a failed font load would otherwise produce a PDF with every glyph missing, silently."""
    from playwright.sync_api import sync_playwright

    libs = os.environ.get("CHROMIUM_LIBS") or str(
        Path.home() / ".cache/pyscotch-chromium-libs/root/usr/lib/x86_64-linux-gnu"
    )
    if Path(libs).is_dir():
        os.environ["LD_LIBRARY_PATH"] = libs + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
    fonts = [(fam, w, base64.b64encode(data).decode()) for fam, w, data in font_files()]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(Path(html).resolve().as_uri())
        bad = page.evaluate(_LOAD_FONTS_JS, fonts)
        if bad:
            sys.exit("font loading failed, refusing to write a glyph-less PDF: " + "; ".join(bad))
        if not page.evaluate(
            "document.fonts.check('400 10pt Inter') && document.fonts.check('400 8pt \"JetBrains Mono\"')"
        ):
            sys.exit("fonts not usable after loading, refusing to write the PDF")
        page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")  # print patch sketches open
        page.emulate_media(media="print")
        page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
        browser.close()
    print("wrote", pdf, f"({Path(pdf).stat().st_size // 1024} KiB)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ingest")
    a.add_argument("--version", required=True)
    a.add_argument("--from", dest="src", required=True)
    a.add_argument("--to", dest="dest", required=True)
    m = sub.add_parser("merge-audit")
    m.add_argument(
        "--from", dest="src", required=True, help="WORKROOT holding <GROUP>/audit.json, extra.json, patches/, alt/"
    )
    m.add_argument("--to", dest="dest", required=True, help="DATA_DIR with an ingested findings.json")
    m.add_argument(
        "--check-apply",
        metavar="SCOTCH_GIT",
        help="git clone to apply every series on, in order, and export them as one series",
    )
    m.add_argument(
        "--order", metavar="FILE", help="groups to apply first, one per line, in this order (rest alphabetical)"
    )
    m.add_argument(
        "--repro-root", metavar="DIR", help="where the version-independent reproducer kits go (upstream/repro)"
    )
    b = sub.add_parser("build")
    b.add_argument("--data", required=True)
    b.add_argument("--pdf", action="store_true")
    b.add_argument("--allow-pending", action="store_true", help="build even if some findings lack our own title")
    b.add_argument(
        "--internal", action="store_true", help="also render the first-pass critique (never for the maintainer)"
    )
    args = ap.parse_args()
    if args.cmd == "ingest":
        ingest(args.version, args.src, args.dest)
    elif args.cmd == "merge-audit":
        merge_audit(args.src, args.dest, args.check_apply, args.order, args.repro_root)
    else:
        build(args.data, args.pdf, args.allow_pending, args.internal)


if __name__ == "__main__":
    main()
