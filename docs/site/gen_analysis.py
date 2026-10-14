#!/usr/bin/env python3
# ruff: noqa: E501  (HTML/JS fragments; readability over width)
"""Render the public "Scotch analysis" section of the docs site from a per-version report data directory.

    gen_analysis.py [--data upstream/reports/<version>] [--out docs/out/analysis]   (default: the newest version)

Writes analysis/index.html (overview + stats), analysis/dashboard.html (every finding, filterable, client-side),
analysis/series.html (combined patch series + QA matrix), analysis/findings/<ID>.html (one page per finding) and
copies the patches, alternatives and the combined series next to them. Raw by design: the audit prose is rendered
as the auditors wrote it. Run after docs/site/build.py (it reuses the site's nav and stylesheet)."""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

SITE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE_DIR))
import build as site_build  # noqa: E402  (the docs site generator: nav + page parsing)

REPO = SITE_DIR.parents[1]
REVIEW = {"author": "R. Perry", "date": "7 Oct 2026", "base": "7.0.16"}
AREAS = {
    "COR": "core & architectures",
    "GRA": "sequential graphs",
    "SEP": "bipartitioning, separators & meshes",
    "API": "library API",
    "DGR": "distributed graphs",
    "DMO": "distributed mapping & ordering",
    "CLI": "tools, METIS shim, esMUMPS",
    "BLD": "build, tests & CI",
}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def source_of(fid):
    if fid.startswith("PS2-"):
        return "PyScotch, second pass"
    if fid.startswith("PS-"):
        return "PyScotch, first pass"
    return f"{REVIEW['author']} review"


def area_of(fid):
    m = re.match(r"(?:PS2?-)?([A-Z]{3})-", fid)
    return AREAS.get(m.group(1), "") if m else ""


def fid(f):
    return f.get("id") or f.get("local_id")


RX_NO_TEST = re.compile(r'^\s*(""|none\b|n/a|;|\(the file is the test)', re.I)


def has_check_test(f):
    """True when the audit added a regression test to the shipped check suite (not a reproducer, not 'no home')."""
    t = (f.get("test_added") or "").strip()
    if not t or RX_NO_TEST.match(t):
        return False
    return bool(re.search(r"src/check|check_[a-z0-9_]+|test_[a-z0-9_]+\.(c|f90)", t))


def blocking(f):
    """Still open upstream and covered by a regression test the PyScotch test bench inherits."""
    return f.get("status") in ("still-present", "partially-fixed") and has_check_test(f)


def status_html(s):
    s = s or ""
    return f'<span class="st st-{esc(s)}">{esc(s)}</span>'


HIST = {}  # id -> {version: status}, from every upstream/reports/<version>/findings.json


def history_of(f, versions):
    h = dict(f.get("history") or {})
    h.update(HIST.get(fid(f), {}))
    if not h:
        h = {"reported": "reported", versions[-1]: f.get("status", "")}
    return h


def nav_and_env():
    pages = sorted(site_build.PAGES_DIR.glob("*.md"))
    nav = [{"title": site_build.parse_page(p)[0], "url": p.stem + ".html", "stem": p.stem} for p in pages]
    nav.append({"title": "API Reference", "url": "api.html", "stem": "api"})
    env = Environment(loader=FileSystemLoader(str(SITE_DIR / "templates")))
    return nav, env.get_template("analysis_base.html")


def pre(text, cls="an-pre"):
    """Real multi-line text as a block; a one-line field (most of them: the auditors joined lines with ' / ' and
    '; ') as prose, with the quoted code fragments ('...') set inline."""
    if not text:
        return ""
    if "\n" in text.strip():
        return f'<pre class="{cls}">{esc(text)}</pre>'
    parts = re.split(r"'([^']{2,}?)'", text)  # odd indexes are the quoted fragments
    out = "".join(f"<code>{esc(p)}</code>" if k % 2 else esc(p) for k, p in enumerate(parts))
    return f'<p class="an-quote">{out}</p>'


def diff_block(rel, out, label=None):
    """A collapsible rendered diff plus a raw link; `rel` is relative to the data dir (patches/..., alt/..., series/...)."""
    p = out / rel
    if not rel or not p.is_file():
        return f'<p class="muted">({esc(rel or "no diff file")} not found)</p>'
    text = p.read_text(errors="replace")
    name = Path(rel).name
    return (
        f'<details class="an-diff"><summary>{esc(label or name)} <a class="muted" href="{esc(rel)}">raw</a>'
        f' <span class="muted">({len(text.splitlines())} lines)</span></summary>{pre(text)}</details>'
    )


KNOWN_IDS = set()


def repro_block(rel, out, grp, heading=True):
    """The reproducer of a finding (README inline + file links) and the group's summary and shared harness.
    `rel` is '<group>/<id>' under upstream/repro/, copied to analysis/repro/."""
    parts = []
    rep_dir = out / "repro" / rel if rel else None
    if rep_dir and rep_dir.is_dir():
        files = sorted(p for p in rep_dir.rglob("*") if p.is_file())
        readme = next((p for p in files if p.name.lower().startswith("readme")), None)
        if heading:
            parts.append("<h2>Reproducer</h2>")
        if readme:
            parts.append(pre(readme.read_text(errors="replace")[:6000]))
        parts.append(
            '<p class="muted">'
            + " · ".join(
                f'<a href="../repro/{esc(rel)}/{esc(p.relative_to(rep_dir).as_posix())}">{esc(p.relative_to(rep_dir).as_posix())}</a>'
                for p in files
            )
            + "</p>"
        )
    if grp and (out / "groups" / grp / "SUMMARY.md").is_file():
        common = (out / "repro" / grp / "common").is_dir()
        parts.append(
            f'<p class="muted">Audited with the <a href="../groups/{esc(grp)}/summary.html">{esc(grp)}</a> group'
            + (f'; shared harness: <a href="../repro/{esc(grp)}/common/">repro/{esc(grp)}/common</a>' if common else "")
            + ".</p>"
        )
    return parts


def finding_page(f, versions, out, series_by_file):
    i = fid(f)
    h = history_of(f, versions)
    cur = versions[-1]
    status = f.get("status") or ""
    sev = f.get("severity") or ""
    parts = [f'<p class="muted">{esc(i)} · {esc(source_of(i))}{" · " + esc(area_of(i)) if area_of(i) else ""}</p>']
    parts.append(f"<h1>{esc(f.get('our_title') or '(no title yet)')}</h1>")
    # one-line verdict
    verdict = {
        "fixed": f"Fixed upstream in {cur}",
        "partially-fixed": f"Partially fixed upstream in {cur}",
        "still-present": f"Still present in {cur}",
        "not-a-bug": "Not a bug",
        "inconclusive": "Inconclusive",
    }.get(status, status)
    if f.get("upstream_change") and status in ("fixed", "partially-fixed"):
        verdict += f" ({esc(f['upstream_change'].split()[0])})"
    npatch = len(f.get("patch_files") or [])
    verdict += f"; {npatch} patch{'es' if npatch > 1 else ''} proposed" if npatch else ""
    verdict += (
        f"; verified by {'running it' if f.get('method') in ('ran', 'reproduced', 'both') else f.get('method', '')}"
        if f.get("method")
        else ""
    )
    parts.append(f"<p><b>{status_html(status)}</b> {esc(verdict)}.</p>")
    parts.append('<dl class="an-kv">')
    timeline = " → ".join(f"{esc(v)}: {status_html(h[v])}" for v in versions if v in h)
    parts.append(
        f"<dt>History</dt><dd>reported in {esc(REVIEW['base'] if not i.startswith('PS') else cur)}"
        f"{' → ' + timeline if timeline else ''}</dd>"
    )
    parts.append(
        f'<dt>Severity</dt><dd><span class="sev-{esc(sev)}">{esc(sev or "—")}</span> (ours)'
        f"{'; the review said ' + esc(f['claimed_severity']).lower() if f.get('claimed_severity') else ''}"
        f"{'<br><span class=muted>' + esc(f['severity_note']) + '</span>' if f.get('severity_note') else ''}</dd>"
    )
    if f.get("needs"):
        parts.append(f"<dt>Could not run</dt><dd>{esc(f['needs'])}: {esc(f.get('needs_note', ''))}</dd>")
    parts.append(
        f"<dt>Location ({esc(cur)})</dt><dd><code>{esc(f.get('location') or f.get('location_7_0_17') or '')}</code></dd>"
    )
    if f.get("upstream_change"):
        parts.append(f"<dt>Upstream change</dt><dd>{esc(f['upstream_change'])}</dd>")
    if f.get("related_review_ids"):
        parts.append(
            "<dt>Related</dt><dd>"
            + ", ".join(
                f'<a href="{esc(r)}.html">{esc(r)}</a>' if r in KNOWN_IDS else esc(r) for r in f["related_review_ids"]
            )
            + "</dd>"
        )
    parts.append("</dl>")
    if f.get("evidence"):
        parts.append("<h2>Evidence</h2>" + pre(f["evidence"]))
    if f.get("ran"):
        parts.append("<h2>What we ran</h2>" + pre(f["ran"]))
    if f.get("read_only") or f.get("why_not_run"):
        parts.append(
            "<h2>Read only</h2><p>" + esc(f.get("read_only", "")) + " " + esc(f.get("why_not_run", "")) + "</p>"
        )
    if f.get("review_accuracy"):
        parts.append("<h2>About the review's lead</h2><p>" + esc(f["review_accuracy"]) + "</p>")
    if f.get("extra_instances"):
        parts.append("<h2>Other instances of the same pattern</h2><ul>")
        for x in f["extra_instances"]:
            parts.append(
                f"<li><code>{esc(x.get('location', ''))}</code> {esc(x.get('quote', ''))}"
                f"{' — covered by the patch' if x.get('covered_by_patch') else ' — not covered'}</li>"
            )
        parts.append("</ul>")
    grp = f.get("group") or ""
    parts.extend(repro_block(f.get("repro"), out, grp))
    for v in f.get("also") or []:
        parts.append(f"<h2>Also audited by {esc(v['group'])}</h2>")
        line = status_html(v.get("status")) + " " + esc(v.get("our_title") or "")
        if v.get("severity"):
            line += f' · <span class="sev-{esc(v["severity"])}">{esc(v["severity"])}</span>'
        parts.append(f"<p>{line}</p>")
        if v.get("notes"):
            parts.append(f'<p class="muted">{esc(v["notes"])}</p>')
        for p in v.get("patch_files") or []:
            s_ = series_by_file.get(p, {})
            parts.append(diff_block(p, out, s_.get("subject") or Path(p).name))
        parts.extend(repro_block(v.get("repro"), out, v["group"], heading=False))
    opts = f.get("fix_options") or []
    if opts:
        parts.append("<h2>Fix options</h2>")
        for o in opts:
            parts.append(
                f'<div class="an-opt{" pref" if o.get("preferred") else ""}"><b>{esc(o.get("label", ""))}</b>'
                f"{' — recommended' if o.get('preferred') and 'recommended' not in (o.get('label') or '').lower() else ''}"
                f"<p>{esc(o.get('summary', ''))}</p>"
            )
            for k, lab in (("tradeoffs", "Trade-offs"), ("tested", "Tested"), ("maintainer_fit", "Maintainer fit")):
                if o.get(k):
                    parts.append(f"<p><b>{lab}:</b> {esc(o[k])}</p>")
            if o.get("diff_file"):
                parts.append(diff_block(o["diff_file"], out))
            parts.append("</div>")
    pf = f.get("patch_files") or []
    if pf:
        parts.append("<h2>Recommended patch" + ("es" if len(pf) > 1 else "") + "</h2>")
        for p in pf:
            s = series_by_file.get(p, {})
            lab = s.get("subject") or Path(p).name
            if s.get("combined_file"):
                lab += f"  (series #{Path(s['combined_file']).name[:4]})"
            parts.append(diff_block(p, out, lab))
    for k, lab in (
        ("cleanup_done", "Cleanup done"),
        ("test_added", "Test added"),
        ("docs_updated", "Docs updated"),
        ("notes", "Notes"),
    ):
        if f.get(k) and f[k].strip().lower() not in ("none needed", "none", "n/a", ""):
            parts.append(f"<h3>{lab}</h3><p>{esc(f[k])}</p>")
    return "\n".join(parts)


def dashboard_rows(items, versions):
    rows = []
    for f in items:
        i = fid(f)
        h = history_of(f, versions)
        rows.append(
            {
                "id": i,
                "src": source_of(i),
                "area": area_of(i),
                "title": f.get("our_title") or "",
                "sev": f.get("severity") or "",
                "status": f.get("status") or "",
                "method": f.get("method") or "",
                "hist": f"{REVIEW['base'] if not i.startswith('PS') else versions[-1]} → "
                + " → ".join(f"{v}: {h[v]}" for v in versions if v in h),
                "patches": len(f.get("patch_files") or []),
                "block": "blocking" if blocking(f) else ("tested" if has_check_test(f) else ""),
                "group": (f.get("group") or "")[:3],
                "loc": (f.get("location") or f.get("location_7_0_17") or "")[:80],
            }
        )
    return rows


DASH_JS = """
<script>
const ROWS = __ROWS__;
const tb = document.querySelector('#an-table tbody'); const q = document.querySelector('#q');
const sel = {src: document.querySelector('#f-src'), status: document.querySelector('#f-status'), sev: document.querySelector('#f-sev'), area: document.querySelector('#f-area'), block: document.querySelector('#f-block')};
let sortKey = 'id', sortDir = 1;
function fill(s, key) { const vals = [...new Set(ROWS.map(r => r[key]).filter(Boolean))].sort(); for (const v of vals) { const o = document.createElement('option'); o.value = v; o.textContent = v; s.appendChild(o); } }
fill(sel.src, 'src'); fill(sel.status, 'status'); fill(sel.sev, 'sev'); fill(sel.area, 'area');
function render() {
  const t = q.value.toLowerCase();
  let rows = ROWS.filter(r => (!sel.src.value || r.src === sel.src.value) && (!sel.status.value || r.status === sel.status.value)
    && (!sel.sev.value || r.sev === sel.sev.value) && (!sel.area.value || r.area === sel.area.value) && (!sel.block.value || r.block === sel.block.value)
    && (!t || (r.id + ' ' + r.title + ' ' + r.loc + ' ' + r.hist).toLowerCase().includes(t)));
  const sevRank = {high: 0, medium: 1, low: 2, info: 3};
  rows.sort((a, b) => { let x = a[sortKey], y = b[sortKey]; if (sortKey === 'sev') { x = sevRank[x] ?? 9; y = sevRank[y] ?? 9; } return (x > y ? 1 : x < y ? -1 : 0) * sortDir; });
  document.querySelector('#an-count').textContent = rows.length + ' of ' + ROWS.length;
  tb.innerHTML = rows.map(r => `<tr><td><a href="findings/${r.id}.html">${r.id}</a></td><td>${r.src}</td><td><a class="t" href="findings/${r.id}.html">${r.title}</a></td><td>${r.area}</td>
    <td class="sev-${r.sev}">${r.sev}</td><td><span class="st st-${r.status}">${r.status}</span></td><td class="muted">${r.hist}</td><td>${r.method}</td><td>${r.patches || ''}</td><td>${r.block === 'blocking' ? '<span class="st st-still-present">blocking</span>' : (r.block === 'tested' ? '<span class="muted">tested</span>' : '')}</td></tr>`).join('');
}
document.querySelectorAll('#an-table th[data-k]').forEach(th => th.addEventListener('click', () => { const k = th.dataset.k; sortDir = (sortKey === k) ? -sortDir : 1; sortKey = k; render(); }));
[q, ...Object.values(sel)].forEach(e => e.addEventListener('input', render));
render();
</script>"""


def main():
    ap = argparse.ArgumentParser()
    newest = sorted(p for p in (REPO / "upstream" / "reports").glob("*") if (p / "findings.json").is_file())
    ap.add_argument(
        "--data", default=str(newest[-1]) if newest else None, help="report data dir (upstream/reports/<version>)"
    )
    ap.add_argument("--out", default=str(REPO / "docs" / "out" / "analysis"))
    a = ap.parse_args()
    data_dir, out = Path(a.data), Path(a.out)
    data = json.load(open(data_dir / "findings.json"))
    ver = data["scotch_version"]
    findings, new = data["findings"], data["new"]
    items = findings + new
    KNOWN_IDS.update(fid(f) for f in items)
    for vd in sorted(data_dir.parent.glob("*/findings.json")):  # every audited version, for the history column
        vdata = json.load(open(vd))
        for x in vdata["findings"] + vdata["new"]:
            HIST.setdefault(fid(x), {})[vdata["scotch_version"]] = x.get("status", "")
    versions = sorted(
        {v for f in items for v in (f.get("history") or {}) if v != "reported"}
        | {ver}
        | {v for h in HIST.values() for v in h}
    )
    qa = json.load(open(data_dir / "qa.json")) if (data_dir / "qa.json").exists() else {}
    series = data.get("series", [])
    series_by_file = {s["file"]: s for s in series}
    combined = data.get("combined") or {}

    out.mkdir(parents=True, exist_ok=True)
    (out / "findings").mkdir(exist_ok=True)
    repro_root = data_dir.parent.parent / "repro"  # upstream/repro: reproducer kits, independent of the version
    for sub, src in (
        ("patches", data_dir),
        ("alt", data_dir),
        ("series", data_dir),
        ("groups", data_dir),
        ("repro", repro_root.parent),
    ):
        shutil.rmtree(out / sub, ignore_errors=True)
        if (src / sub).is_dir():
            shutil.copytree(src / sub, out / sub)
    shutil.rmtree(out / "audit", ignore_errors=True)  # layout before upstream/repro existed
    nav, tpl = nav_and_env()

    def write(name, title, content, root="../", current="", width=None):
        base = "../" if "/" in name else ""
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(
            tpl.render(title=title, content=content, root=root, base=base, current=current, ver=ver, width=width)
        )

    # per-finding pages (links inside them are relative to analysis/: prefix ../ for sibling resources)
    for f in items:
        page = (
            finding_page(f, versions, out, series_by_file)
            .replace('href="patches/', 'href="../patches/')
            .replace('href="alt/', 'href="../alt/')
            .replace('href="series/', 'href="../series/')
        )
        write(f"findings/{fid(f)}.html", fid(f), page, root="../../", width="52rem")

    # dashboard
    rows = dashboard_rows(items, versions)
    counts = {
        k: sum(1 for r in rows if r["status"] == k)
        for k in ("still-present", "fixed", "partially-fixed", "not-a-bug", "inconclusive")
    }
    tiles = [
        (len(findings), f"leads in the {REVIEW['author']} review"),
        (len(new), "further defects found by PyScotch"),
        (sum(1 for r in rows if r["patches"]), "findings with a recommended patch"),
        (counts["still-present"], f"still present in {ver}"),
        (counts["fixed"] + counts["partially-fixed"], f"fixed or partially fixed upstream in {ver}"),
        (sum(1 for r in rows if r["sev"] == "high"), "rated high by us"),
        (sum(1 for r in rows if r["block"] == "blocking"), "blocking for the next PyScotch release"),
    ]
    blk = sorted(
        (r for r in rows if r["block"] == "blocking"),
        key=lambda r: ({"high": 0, "medium": 1, "low": 2, "info": 3}.get(r["sev"], 9), r["id"]),
    )
    blk_html = (
        f'<h2 id="blocking">Blocking for the next PyScotch release <span class="muted">({len(blk)})</span></h2>'
        '<p class="muted">Still open upstream, and the fix ships with a regression test in Scotch\'s own check suite. '
        "PyScotch ports those tests and runs them against the library it bundles, so these must be fixed upstream or "
        "carried as PyScotch patches before the next release.</p>"
        '<table class="an"><tr><th>id</th><th>title</th><th>severity</th><th>status</th></tr>'
        + "".join(
            f'<tr><td><a href="findings/{esc(r["id"])}.html">{esc(r["id"])}</a></td>'
            f'<td><a class="t" href="findings/{esc(r["id"])}.html">{esc(r["title"])}</a></td>'
            f'<td class="sev-{esc(r["sev"])}">{esc(r["sev"])}</td><td>{status_html(r["status"])}</td></tr>'
            for r in blk
        )
        + "</table>"
    )
    tiles_html = (
        '<div class="an-tiles">'
        + "".join(f'<div class="an-tile"><b>{n}</b><span>{esc(t)}</span></div>' for n, t in tiles)
        + "</div>"
    )
    controls = (
        '<div class="an-controls"><input id="q" placeholder="search id, title, location…" size="32">'
        '<select id="f-src"><option value="">any source</option></select><select id="f-status"><option value="">any status</option></select>'
        '<select id="f-sev"><option value="">any severity</option></select><select id="f-area"><option value="">any area</option></select>'
        '<select id="f-block"><option value="">PyScotch: any</option><option value="blocking">blocking</option><option value="tested">tested, not blocking</option></select>'
        '<span class="muted" id="an-count"></span></div>'
    )
    table = (
        '<table class="an" id="an-table"><thead><tr><th data-k="id">id</th><th data-k="src">source</th><th data-k="title">title (our words)</th>'
        '<th data-k="area">area</th><th data-k="sev">severity</th><th data-k="status">status</th><th data-k="hist">history</th>'
        '<th data-k="method">verified</th><th data-k="patches">patch</th><th data-k="block">PyScotch</th></tr></thead><tbody></tbody></table>'
    )
    dash = (
        f"<h1>Scotch {esc(ver)} AI analysis: all the findings</h1>"
        + tiles_html
        + blk_html
        + "<h2>All the findings</h2>"
        + controls
        + table
        + DASH_JS.replace("__ROWS__", json.dumps(rows, ensure_ascii=False))
    )
    write("index.html", "Dashboard", dash, current="index")

    # series page
    s_rows = []
    for s in series:
        dup = s.get("duplicate_of")
        num = Path(s["combined_file"]).name[:4] if s.get("combined_file") else "—"
        s_rows.append(
            f'<tr><td>{esc(num)}</td><td class="muted">{esc(s["group"][:3])}</td><td><a href="{esc(s["file"])}">{esc(s["subject"])}</a>'
            f"{' <span class=muted>(same fix as ' + esc(Path(dup).parent.name[:3] + '/' + Path(dup).name[:4]) + ')</span>' if dup else ''}</td>"
            f"<td>{' '.join(f'<a href=findings/{esc(i)}.html>{esc(i)}</a>' for i in s['ids'])}</td></tr>"
        )
    qa_html = ""
    if qa:
        qa_html = '<h2>Build and test matrix</h2><table class="an"><tr><th>suite</th><th>pristine, 32-bit</th><th>with the series, 32-bit</th><th>pristine, 64-bit</th><th>with the series, 64-bit</th></tr>'
        qa_html += "".join(
            f"<tr><td>{esc(r['suite'])}</td><td>{esc(r['pristine32'])}</td><td>{esc(r['patched32'])}</td><td>{esc(r['pristine64'])}</td><td>{esc(r['patched64'])}</td></tr>"
            for r in qa.get("suites", [])
        )
        qa_html += (
            "</table><ul>"
            + "".join(f"<li>{esc(b['tree'])}: {b['warnings']} warnings</li>" for b in qa.get("builds", []))
            + "".join(f"<li>{esc(n)}</li>" for n in qa.get("notes", []))
            + "</ul>"
        )
    ser = (
        f"<h1>Patch series on v{esc(ver)}</h1><p>{len(series)} commits from {len(data.get('audited_groups', []))} audit groups, "
        f"{sum(1 for s in series if s.get('duplicate_of'))} duplicates dropped, {combined.get('count', 0)} distinct patches. "
        f"They apply in this order on v{esc(ver)} with a plain <code>git am</code>: {'verified' if combined.get('plain_apply') else 'NOT verified'}. "
        f'One numbered series: <a href="series/">series/</a>.</p>'
        + qa_html
        + '<h2>The commits</h2><table class="an"><tr><th>#</th><th>group</th><th>subject</th><th>findings</th></tr>'
        + "".join(s_rows)
        + "</table>"
    )
    groups_html = ""
    adir = out / "groups"
    if adir.is_dir():
        rows_g = []
        for gd in sorted(p for p in adir.iterdir() if p.is_dir()):
            sm = gd / "SUMMARY.md"
            if sm.is_file():
                (gd / "summary.html").write_text(
                    tpl.render(
                        title=gd.name,
                        content=f"<h1>{esc(gd.name)}</h1>" + pre(sm.read_text(errors="replace")),
                        root="../../../",
                        base="../../",
                        current="series",
                        ver=ver,
                        width="60rem",
                    )
                )
            npatch = sum(1 for x in series if x["group"] == gd.name and not x.get("duplicate_of"))
            kit = out / "repro" / gd.name
            nrep = len([p for p in kit.iterdir() if p.is_dir() and p.name in KNOWN_IDS]) if kit.is_dir() else 0
            rows_g.append(
                f'<tr><td><a href="groups/{esc(gd.name)}/summary.html">{esc(gd.name)}</a></td><td>{npatch}</td>'
                f"<td>{f'<a href=repro/{esc(gd.name)}/>{nrep}</a>' if kit.is_dir() else '0'}</td>"
                f'<td><a href="groups/{esc(gd.name)}/audit.json">audit.json</a> · <a href="groups/{esc(gd.name)}/extra.json">extra.json</a></td></tr>'
            )
            dirs = [gd] + ([kit] + [p for p in kit.rglob("*") if p.is_dir()] if kit.is_dir() else [])
            for dd in dirs:  # static hosts do not list directories
                if not (dd / "index.html").exists():
                    ents = sorted(p for p in dd.iterdir() if p.name != "index.html")
                    (dd / "index.html").write_text(
                        "<!doctype html><meta charset=utf-8><title>"
                        + esc(dd.name)
                        + "</title><h1>"
                        + esc(dd.relative_to(out).as_posix())
                        + "</h1><ul>"
                        + "".join(
                            f'<li><a href="{esc(p.name)}{"/" if p.is_dir() else ""}">{esc(p.name)}{"/" if p.is_dir() else ""}</a></li>'
                            for p in ents
                        )
                        + "</ul>"
                    )
        groups_html = (
            '<h2>Audit groups</h2><p class="muted">One agent per group of source files; each summary is the agent\'s own report, raw.</p>'
            '<table class="an"><tr><th>group</th><th>patches</th><th>reproducers</th><th>raw audit</th></tr>'
            + "".join(rows_g)
            + "</table>"
        )
    ser += groups_html
    write("series.html", "Patch series", ser, current="series")

    # about page (acknowledgements, method) from docs/site/analysis_about.md
    about_md = site_build.parse_page(SITE_DIR / "analysis_about.md")[1]
    write(
        "about.html",
        "What is this?",
        site_build.render_markdown_with_examples(about_md),
        current="about",
        width="46rem",
    )
    # a directory listing for series/ (static hosts do not list)
    files = sorted(p.name for p in (out / "series").glob("*.patch")) if (out / "series").is_dir() else []
    (out / "series" / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>series</title><h1>Combined series</h1><ol>"
        + "".join(f'<li><a href="{esc(n)}">{esc(n)}</a></li>' for n in files)
        + "</ol>"
    )
    print(f"analysis: {len(items)} finding pages, {len(series)} series rows -> {out}")


if __name__ == "__main__":
    main()
