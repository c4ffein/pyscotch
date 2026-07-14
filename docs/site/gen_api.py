#!/usr/bin/env python3
"""
API reference generator for the PyScotch documentation site.

Two halves, deliberately separated so the docs site can be built WITHOUT a
compiled Scotch:

- collect_data() imports pyscotch, walks its public classes/functions reading
  the @scotch_binding / @highlevel_api decorator metadata, and returns a plain
  data dict. This needs a built libscotch (importing pyscotch dlopens it).
- render_html(data) / api_sections_from(data) turn that data dict into HTML.
  Pure — no pyscotch import, only the committed manual-page map.

The data is cached to api_data.json (committed). build.py renders from that
JSON, so deploying the site needs no C build. Regenerate after any API change:

    python docs/site/gen_api.py --dump        # writes docs/site/api_data.json

A CI job re-runs that and `git diff --exit-code`s to catch a stale file.
"""

import argparse
import html
import inspect
import json
import re
from pathlib import Path

SITE_DIR = Path(__file__).parent
DATA_PATH = SITE_DIR / "api_data.json"

# API level -> (badge label, badge CSS suffix, C function list label)
LEVELS = {
    "scotch_binding": ("direct binding", "binding", "Maps to"),
    "highlevel": ("high-level helper", "helper", "Wraps"),
    "internal": ("pure python", "python", "Calls"),
    None: ("undecorated", "undecorated", "Calls (detected)"),
}

# {SCOTCH_function: {"pdf": ..., "page": ...}} extracted from the manuals'
# bookmarks by gen_pdf_map.py. Links point at INRIA's GitLab, pinned to the
# tag the page map was extracted from — bump the tag AND rerun gen_pdf_map.py
# together, or the page numbers drift.
_MAP_PATH = SITE_DIR / "scotch_manual_pages.json"
MANUAL_PAGES = json.loads(_MAP_PATH.read_text()) if _MAP_PATH.exists() else {}
SCOTCH_DOC_TAG = "v7.0.11"
_MANUAL_URL = "https://gitlab.inria.fr/scotch/scotch/-/raw/{tag}/doc/{pdf}?inline=true"


# ---------------------------------------------------------------------------
# Data collection (imports pyscotch — needs a built libscotch)
# ---------------------------------------------------------------------------


def first_paragraph(doc):
    """First docstring paragraph, collapsed to a single line."""
    if not doc:
        return ""
    return " ".join(inspect.cleandoc(doc).split("\n\n")[0].split())


def signature_of(func):
    """Python signature as a string, without the leading self/cls.

    NOTE: annotation stringification is Python-version-dependent (<=3.13 renders
    "Optional[X]" / "Union[A, B]"; 3.14+ uses PEP 604 pipes "X | None" / "A | B").
    collect_data() therefore requires Python >= 3.14 so the committed
    api_data.json is reproducible — see the guard there.
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return "(...)"
    params = list(sig.parameters.values())
    if params and params[0].name in ("self", "cls"):
        sig = sig.replace(parameters=params[1:])
    return str(sig)


def detected_calls(func, declared):
    """Fallback for undecorated methods: scan the source for lib.SCOTCH_* calls.

    Only names present in the declared-binding set are kept, which filters out
    ctypes types such as SCOTCH_Num.
    """
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        return []
    names = set(re.findall(r"\blib\.(SCOTCH_\w+)", source))
    return sorted(names & declared)


def make_entry(name, func, declared, is_property=False):
    """Describe one public method or function."""
    level = getattr(func, "_api_level", None)
    if level == "scotch_binding":
        c_functions = [func._scotch_function]
    elif level == "highlevel":
        c_functions = list(func._wraps_scotch)
    else:
        c_functions = detected_calls(func, declared)
    label, css, c_label = LEVELS.get(level, LEVELS[None])
    return {
        "name": name,
        "signature": "" if is_property else signature_of(func),
        "summary": first_paragraph(func.__doc__),
        "level": label,
        "level_css": css,
        "c_label": c_label,
        "c_functions": c_functions,
        "is_property": is_property,
    }


def class_entries(cls, declared):
    """Entries for the public methods of a class, in definition order."""
    entries = []
    for name, obj in vars(cls).items():
        if name.startswith("_"):
            continue
        if isinstance(obj, (staticmethod, classmethod)):
            entries.append(make_entry(name, obj.__func__, declared))
        elif isinstance(obj, property):
            entries.append(make_entry(name, obj.fget, declared, is_property=True))
        elif inspect.isfunction(obj):
            entries.append(make_entry(name, obj, declared))
    return entries


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _coverage(sections, declared):
    """Coverage counts for the summary block."""
    entries = [e for s in sections for e in s["entries"]]
    exposed = declared & {c for e in entries for c in e["c_functions"]}
    return {
        "direct": sum(e["level"] == "direct binding" for e in entries),
        "helpers": sum(e["level"] == "high-level helper" for e in entries),
        "python": sum(e["level"] == "pure python" for e in entries),
        "undecorated": sum(e["level"] == "undecorated" for e in entries),
        "declared": len(declared),
        "exposed": len(exposed),
    }


def collect_data():
    """Import pyscotch and return the full API-reference data dict.

    This is the ONLY function that imports pyscotch (which dlopens libscotch),
    so it is the only part that needs a compiled Scotch. Loads the 64-bit
    parallel variant so the Dgraph bindings are counted in coverage.
    """
    import os
    import sys

    # Annotation stringification (Optional/Union) is Python-version-dependent —
    # <=3.13 renders "Optional[X]", 3.14+ renders "X | None" — so the committed
    # api_data.json is only reproducible on one interpreter. We standardize on
    # 3.14+ (the PEP 604 pipe form). Fail loudly rather than silently emit a
    # file that the docs-verify CI job (which runs 3.14) will flag as stale.
    if sys.version_info < (3, 14):
        raise SystemExit(
            "gen_api.py --dump requires Python >= 3.14 (you are on "
            f"{sys.version_info.major}.{sys.version_info.minor}). Type annotations "
            "stringify differently on older versions, producing a spuriously "
            "'stale' api_data.json. Try: uv run --python 3.14 python "
            "docs/site/gen_api.py --dump"
        )

    os.environ.setdefault("PYSCOTCH_INT_SIZE", "64")
    os.environ.setdefault("PYSCOTCH_PARALLEL", "1")
    root = SITE_DIR.parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import pyscotch
    from pyscotch import libscotch

    declared = set(libscotch._DECLARED_BINDINGS)

    sections, functions = [], []
    for name in pyscotch.__all__:
        obj = getattr(pyscotch, name)
        if inspect.isclass(obj):
            sections.append(
                {
                    "name": name,
                    "slug": slugify(name),
                    "doc": html.escape(first_paragraph(obj.__doc__)),
                    "entries": class_entries(obj, declared),
                }
            )
        elif inspect.isfunction(obj):
            functions.append(make_entry(name, obj, declared))
    sections.append(
        {
            "name": "Module functions",
            "slug": "module-functions",
            "doc": "Functions available directly on the <code>pyscotch</code> module.",
            "entries": functions,
        }
    )
    return {
        "version": ".".join(str(v) for v in pyscotch.scotch_version()),
        "coverage": _coverage(sections, declared),
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# Rendering (pure — no pyscotch, reads the committed data + manual map)
# ---------------------------------------------------------------------------


def manual_entry(c_function):
    """(href, hover_text) into the Scotch manual for c_function, or None."""
    entry = MANUAL_PAGES.get(c_function)
    if not entry:
        return None
    manual = "PT-Scotch" if "ptscotch" in entry["pdf"] else "Scotch"
    url = _MANUAL_URL.format(tag=SCOTCH_DOC_TAG, pdf=entry["pdf"])
    return f'{url}#page={entry["page"]}', f'{manual} user manual, page {entry["page"]}'


def manual_link(c_function):
    """<a> to the Scotch manual page documenting c_function, or plain <code>."""
    escaped = html.escape(c_function)
    entry = manual_entry(c_function)
    if entry is None:
        return f"<code>{escaped}</code>"
    href, hover = entry
    return (
        f'<a class="api-c-link" href="{href}" target="_blank" rel="noopener" '
        f'title="{hover}"><code>{escaped}</code></a>'
    )


def split_params(body):
    """Split a signature body on top-level commas (brackets may nest)."""
    params, depth, current = [], 0, ""
    for ch in body:
        if ch == "," and depth == 0:
            params.append(current.strip())
            current = ""
            continue
        depth += ch in "([{"
        depth -= ch in ")]}"
        current += ch
    if current.strip():
        params.append(current.strip())
    return params


def format_signature(name, sig):
    """`name(sig)`, one parameter per line when the one-liner gets long."""
    one_line = f"{name}{sig}"
    if len(one_line) <= 72:
        return one_line
    body, arrow, ret = sig.partition(" -> ")
    params = split_params(body[1:-1])  # strip the outer parentheses
    lines = [f"{name}("]
    lines += [f"    {p}," for p in params]
    lines.append(f"){arrow}{ret}")
    return "\n".join(lines)


def badge_tooltip(e):
    """Hover text for the API-level badge."""
    funcs = ", ".join(e["c_functions"])
    if e["level"] == "direct binding":
        return f"1:1 wrapper of {funcs}" if funcs else "1:1 wrapper of a Scotch C function"
    if e["level"] == "high-level helper":
        return f"Composes {funcs}" if funcs else "Pythonic helper"
    if e["level"] == "pure python":
        return "Pure Python — makes no Scotch C call"
    return "Not yet annotated; C calls detected from the source"


def render_entry(e):
    shown = e["name"] if e["is_property"] else format_signature(e["name"], e["signature"])
    tooltip = html.escape(badge_tooltip(e))

    badges = (
        f'<span class="api-badge api-badge-{e["level_css"]}" title="{tooltip}">'
        f'{e["level"]}</span>'
    )
    if e["is_property"]:
        badges = '<span class="api-badge api-badge-property">property</span>' + badges

    # Meta line on top: badge, then the C functions as plain, Ctrl-F-able
    # (and manual-linked) text.
    meta = [badges]
    if e["c_functions"]:
        funcs = ", ".join(manual_link(f) for f in e["c_functions"])
        meta.append(f'<span class="api-method-c">{e["c_label"]}: {funcs}</span>')

    multi = " api-sig-multi" if "\n" in shown else ""
    out = ['<div class="api-method">']
    out.append(f'<div class="api-method-meta">{" ".join(meta)}</div>')
    out.append(f'<div class="api-method-head{multi}"><code>{html.escape(shown)}</code></div>')
    if e["summary"]:
        out.append(f'<p class="api-method-doc">{html.escape(e["summary"])}</p>')
    out.append("</div>")
    return "\n".join(out)


def render_html(data):
    """Full inner HTML for the API reference page, from a collected data dict."""
    sections = data["sections"]
    cov = data["coverage"]
    out = ["<h1>API Reference</h1>"]
    out.append(
        "<p>This page is generated from <code>docs/site/api_data.json</code> "
        "(produced by <code>docs/site/gen_api.py</code> straight from PyScotch's "
        "decorator registries, and CI-checked against the code) — it can never "
        f"drift from the API. Built against Scotch {data['version']}.</p>"
    )
    stats = [
        (cov["direct"], "direct bindings"),
        (cov["helpers"], "high-level helpers"),
        (cov["python"], "pure-python methods"),
        (f"{cov['exposed']} / {cov['declared']}", "declared C bindings exposed via methods"),
    ]
    if cov["undecorated"]:
        stats.insert(3, (cov["undecorated"], "undecorated methods"))
    out.append('<div class="api-summary">')
    for num, label in stats:
        out.append(
            f'<div class="api-stat"><span class="api-stat-num">{num}</span>'
            f'<span class="api-stat-label">{label}</span></div>'
        )
    out.append("</div>")
    out.append(
        '<p class="api-legend"><strong>Badges:</strong> '
        "<em>direct binding</em> — wraps exactly one Scotch C function, 1:1; "
        "<em>high-level helper</em> — a Pythonic method composing several C calls; "
        "<em>pure python</em> — makes no Scotch C call (result containers, accessors). "
        "C function names link to the section of the Scotch / PT-Scotch user "
        "manual documenting them.</p>"
    )
    for section in sections:
        out.append(f'<h2 id="{section["slug"]}">{html.escape(section["name"])}</h2>')
        if section["doc"]:
            out.append(f'<p>{section["doc"]}</p>')
        for e in section["entries"]:
            out.append(render_entry(e))
    return "\n".join(out)


def api_sections_from(data):
    """Names and anchor slugs of the API sections, for the sidebar submenu."""
    return [{"name": s["name"], "slug": s["slug"]} for s in data["sections"]]


def load_data():
    """Read the committed api_data.json, or None if it is absent."""
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyScotch API reference generator")
    parser.add_argument(
        "--dump",
        action="store_true",
        help="collect from pyscotch and write api_data.json (needs a built Scotch)",
    )
    args = parser.parse_args()
    if args.dump:
        DATA_PATH.write_text(json.dumps(collect_data(), indent=1, sort_keys=True) + "\n")
        print(f"wrote {DATA_PATH}")
    else:
        print(render_html(collect_data()))
