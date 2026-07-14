#!/usr/bin/env python3
"""
API reference generator for the PyScotch documentation site.

Imports pyscotch and walks its public classes and functions, reading the
@scotch_binding / @highlevel_api decorator metadata (pyscotch/api_decorators.py)
so the reference can never drift from the code. Methods without a decorator
still appear, flagged "undecorated", with their `lib.SCOTCH_*` calls detected
by scanning the source.

Importing pyscotch prints library load lines to stderr — that's normal.
Requires the Scotch libraries to be built (`make build-all`); build.py falls
back to a placeholder page when this module fails to import.
"""

import html
import inspect
import json
import os
import re
import sys
from pathlib import Path

# Load the 64-bit parallel variant so Dgraph is available
os.environ.setdefault("PYSCOTCH_INT_SIZE", "64")
os.environ.setdefault("PYSCOTCH_PARALLEL", "1")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pyscotch  # noqa: E402
from pyscotch import libscotch  # noqa: E402

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
_MAP_PATH = Path(__file__).parent / "scotch_manual_pages.json"
MANUAL_PAGES = json.loads(_MAP_PATH.read_text()) if _MAP_PATH.exists() else {}
SCOTCH_DOC_TAG = "v7.0.11"
_MANUAL_URL = "https://gitlab.inria.fr/scotch/scotch/-/raw/{tag}/doc/{pdf}?inline=true"


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


def first_paragraph(doc):
    """First docstring paragraph, collapsed to a single line."""
    if not doc:
        return ""
    return " ".join(inspect.cleandoc(doc).split("\n\n")[0].split())


def signature_of(func):
    """Python signature as a string, without the leading self/cls."""
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return "(...)"
    params = list(sig.parameters.values())
    if params and params[0].name in ("self", "cls"):
        sig = sig.replace(parameters=params[1:])
    return str(sig)


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


def detected_calls(func):
    """Fallback for undecorated methods: scan the source for lib.SCOTCH_* calls.

    Only names present in libscotch._DECLARED_BINDINGS are kept, which filters
    out ctypes types such as SCOTCH_Num.
    """
    try:
        source = inspect.getsource(func)
    except (OSError, TypeError):
        return []
    names = set(re.findall(r"\blib\.(SCOTCH_\w+)", source))
    return sorted(names & set(libscotch._DECLARED_BINDINGS))


def make_entry(name, func, is_property=False):
    """Describe one public method or function."""
    level = getattr(func, "_api_level", None)
    if level == "scotch_binding":
        c_functions = [func._scotch_function]
    elif level == "highlevel":
        c_functions = list(func._wraps_scotch)
    else:
        c_functions = detected_calls(func)
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


def class_entries(cls):
    """Entries for the public methods of a class, in definition order."""
    entries = []
    for name, obj in vars(cls).items():
        if name.startswith("_"):
            continue
        if isinstance(obj, (staticmethod, classmethod)):
            entries.append(make_entry(name, obj.__func__))
        elif isinstance(obj, property):
            entries.append(make_entry(name, obj.fget, is_property=True))
        elif inspect.isfunction(obj):
            entries.append(make_entry(name, obj))
    return entries


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def collect():
    """One section per public class, plus one for module-level functions."""
    sections = []
    functions = []
    for name in pyscotch.__all__:
        obj = getattr(pyscotch, name)
        if inspect.isclass(obj):
            sections.append(
                {
                    "name": name,
                    "slug": slugify(name),
                    "doc": html.escape(first_paragraph(obj.__doc__)),
                    "entries": class_entries(obj),
                }
            )
        elif inspect.isfunction(obj):
            functions.append(make_entry(name, obj))
    sections.append(
        {
            "name": "Module functions",
            "slug": "module-functions",
            "doc": "Functions available directly on the <code>pyscotch</code> module.",
            "entries": functions,
        }
    )
    return sections


def coverage(sections):
    """Coverage counts for the summary block."""
    entries = [e for s in sections for e in s["entries"]]
    declared = set(libscotch._DECLARED_BINDINGS)
    exposed = declared & {c for e in entries for c in e["c_functions"]}
    return {
        "direct": sum(e["level"] == "direct binding" for e in entries),
        "helpers": sum(e["level"] == "high-level helper" for e in entries),
        "python": sum(e["level"] == "pure python" for e in entries),
        "undecorated": sum(e["level"] == "undecorated" for e in entries),
        "declared": len(declared),
        "exposed": len(exposed),
    }


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


def generate_api_html():
    """Full inner HTML for the API reference page."""
    sections = collect()
    cov = coverage(sections)
    version = ".".join(str(v) for v in pyscotch.scotch_version())
    out = ["<h1>API Reference</h1>"]
    out.append(
        "<p>This page is generated at build time by <code>docs/site/gen_api.py</code>, "
        "straight from PyScotch's decorator registries "
        "(<code>pyscotch/api_decorators.py</code>) — it can never drift from the code. "
        f"Built against Scotch {version}.</p>"
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


def api_sections():
    """Names and anchor slugs of the API sections, for the sidebar submenu."""
    return [{"name": s["name"], "slug": s["slug"]} for s in collect()]


if __name__ == "__main__":
    print(generate_api_html())
