#!/usr/bin/env python3
"""
Static site builder for PyScotch documentation.

Reads markdown pages from pages/, embeds example .py files via {% example %} tags,
and outputs HTML to docs/out/.

Usage:
    python docs/site/build.py
"""

import re
import sys
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

# GitHub Primer (light) token colors for Pygments classes — the palette
# GitHub itself renders Python with, on white code surfaces.
GITHUB_LIGHT_CSS = """
.example code .k, .example code .kn, .example code .kc, .example code .kd,
.example code .kp, .example code .kr, .example code .kt, .example code .ow
{ color: #cf222e; }
.example code .nf, .example code .fm, .example code .nd, .example code .nc
{ color: #8250df; }
.example code .s, .example code .s1, .example code .s2, .example code .sd,
.example code .sa, .example code .si, .example code .se, .example code .sr
{ color: #0a3069; }
.example code .m, .example code .mi, .example code .mf, .example code .mh,
.example code .mo, .example code .nb, .example code .bp, .example code .no
{ color: #0550ae; }
.example code .c, .example code .c1, .example code .cm, .example code .cs,
.example code .ch
{ color: #59636e; }
.example code .o, .example code .p { color: inherit; }
.example code .err { color: inherit; border: none; }
"""

SITE_DIR = Path(__file__).parent
PAGES_DIR = SITE_DIR / "pages"
EXAMPLES_DIR = SITE_DIR / "examples"
TEMPLATES_DIR = SITE_DIR / "templates"
STATIC_DIR = SITE_DIR / "static"
OUT_DIR = SITE_DIR.parent / "out"


def read_example(filename):
    """Read a .py example file and return syntax-highlighted HTML."""
    path = EXAMPLES_DIR / filename
    if not path.exists():
        return f'<div class="example error">Example not found: {filename}</div>'
    code = path.read_text()
    html = highlight(code, PythonLexer(), HtmlFormatter(nowrap=True))
    return f'<div class="example"><div class="example-header">{filename}</div><pre><code>{html}</code></pre></div>'


def parse_page(path):
    """Parse a markdown page, extracting frontmatter title and body."""
    text = path.read_text()
    title = path.stem.split("_", 1)[-1].replace("_", " ").title()
    # Extract title from first # heading if present
    first_line = text.split("\n")[0]
    if first_line.startswith("# "):
        title = first_line[2:].strip()
    return title, text


def render_markdown_with_examples(text):
    """First pass: resolve {% example %} tags. Second pass: render markdown."""

    # Replace {% example "filename.py" %} with highlighted code
    def replace_example(match):
        filename = match.group(1)
        return read_example(filename)

    text = re.sub(r'\{%\s*example\s+"([^"]+)"\s*%\}', replace_example, text)

    # Render markdown (the example blocks are already HTML, markdown will pass them through)
    md = markdown.Markdown(extensions=["fenced_code", "codehilite", "toc", "tables"])
    html = md.convert(text)
    return html


API_PLACEHOLDER = """<h1>API Reference</h1>
<p>This page is rendered from <code>docs/site/api_data.json</code>, which is
missing from this checkout.</p>
<blockquote><p>Regenerate it with
<code>python docs/site/gen_api.py --dump</code> (needs a built Scotch), then
rebuild the site with <code>python docs/site/build.py</code>.</p></blockquote>
"""


def build_api_content():
    """API reference HTML and section anchors from the committed api_data.json.

    Renders purely from JSON — no pyscotch import, so the site builds without a
    compiled Scotch. Regenerate the JSON with `python docs/site/gen_api.py
    --dump` after any API change (a CI job checks it is not stale).
    """
    sys.path.insert(0, str(SITE_DIR))
    import gen_api

    data = gen_api.load_data()
    if data is None:
        print(
            "  ! api.html: docs/site/api_data.json missing — run "
            "'python docs/site/gen_api.py --dump'; writing placeholder",
            file=sys.stderr,
        )
        return API_PLACEHOLDER, []
    return gen_api.render_html(data), gen_api.api_sections_from(data)


def build():
    """Build the site."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy static files
    static_out = OUT_DIR / "static"
    static_out.mkdir(exist_ok=True)
    for f in STATIC_DIR.iterdir():
        (static_out / f.name).write_text(f.read_text())

    # The API reference deep-links into the Scotch manuals on INRIA's GitLab
    # (see gen_api.SCOTCH_DOC_TAG) — remove any manuals a previous build
    # copied locally.
    for pdf in ("scotch_user7.0.pdf", "ptscotch_user7.0.pdf"):
        (static_out / pdf).unlink(missing_ok=True)

    # Set up Jinja
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("base.html")

    # Collect and sort pages; the API reference is appended as a generated page
    pages = sorted(PAGES_DIR.glob("*.md"))
    nav = []
    for p in pages:
        title, _ = parse_page(p)
        slug = p.stem + ".html"
        nav.append({"title": title, "url": slug, "stem": p.stem})
    nav.append({"title": "API Reference", "url": "api.html", "stem": "api"})

    # Render each page (markdown pages first, then the generated API reference)
    contents = [render_markdown_with_examples(parse_page(p)[1]) for p in pages]
    api_html, api_sections = build_api_content()
    contents.append(api_html)

    for i, item in enumerate(nav):
        prev_page = nav[i - 1] if i > 0 else None
        next_page = nav[i + 1] if i < len(nav) - 1 else None

        html = template.render(
            title=item["title"],
            content=contents[i],
            nav=nav,
            current=item["stem"],
            prev_page=prev_page,
            next_page=next_page,
            api_sections=api_sections,
            pygments_css=GITHUB_LIGHT_CSS,
        )

        (OUT_DIR / item["url"]).write_text(html)
        print(f"  {item['url']}")

    # Generate index redirect
    if nav:
        index_html = f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url={nav[0]["url"]}"></head></html>'
        (OUT_DIR / "index.html").write_text(index_html)

    print(f"\nBuilt {len(nav)} pages to {OUT_DIR}/")


if __name__ == "__main__":
    build()
