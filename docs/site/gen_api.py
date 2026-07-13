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
    None: ("undecorated", "undecorated", "Calls (detected)"),
}


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
                    "doc": html.escape(first_paragraph(obj.__doc__)),
                    "entries": class_entries(obj),
                }
            )
        elif inspect.isfunction(obj):
            functions.append(make_entry(name, obj))
    sections.append(
        {
            "name": "Module functions",
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
        "undecorated": sum(e["level"] == "undecorated" for e in entries),
        "declared": len(declared),
        "exposed": len(exposed),
    }


def render_entry(e):
    name = html.escape(e["name"])
    sig = html.escape(e["signature"])
    badges = f'<span class="api-badge api-badge-{e["level_css"]}">{e["level"]}</span>'
    if e["is_property"]:
        badges = '<span class="api-badge api-badge-property">property</span>' + badges
    out = ['<div class="api-method">']
    out.append(f'<div class="api-method-head"><code>{name}{sig}</code>{badges}</div>')
    if e["summary"]:
        out.append(f'<p class="api-method-doc">{html.escape(e["summary"])}</p>')
    if e["c_functions"]:
        funcs = ", ".join(f"<code>{html.escape(f)}</code>" for f in e["c_functions"])
        out.append(f'<p class="api-method-c">{e["c_label"]}: {funcs}</p>')
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
        (cov["undecorated"], "undecorated methods"),
        (f"{cov['exposed']} / {cov['declared']}", "declared C bindings exposed via methods"),
    ]
    out.append('<div class="api-summary">')
    for num, label in stats:
        out.append(
            f'<div class="api-stat"><span class="api-stat-num">{num}</span>'
            f'<span class="api-stat-label">{label}</span></div>'
        )
    out.append("</div>")
    for section in sections:
        out.append(f'<h2>{html.escape(section["name"])}</h2>')
        if section["doc"]:
            out.append(f'<p>{section["doc"]}</p>')
        for e in section["entries"]:
            out.append(render_entry(e))
    return "\n".join(out)


if __name__ == "__main__":
    print(generate_api_html())
