#!/usr/bin/env python3
"""
Extract the {SCOTCH_function: manual page} map from the Scotch user manuals.

Reads the PDF bookmarks of scotch_user7.0.pdf and ptscotch_user7.0.pdf in the
scotch submodule and writes scotch_manual_pages.json next to this script.
The JSON is committed so building the docs site needs no PDF tooling; rerun
this script when the submodule's manuals change.

Requires pypdf (optional tooling dependency, NOT needed by build.py):
    uv pip install pypdf
    python docs/site/gen_pdf_map.py
"""

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
DOC_DIR = ROOT / "external" / "scotch" / "doc"
OUT_PATH = Path(__file__).parent / "scotch_manual_pages.json"

# ptscotch entries are collected last so SCOTCH_dgraph* functions point at the
# PT-Scotch manual even if both manuals mention them.
MANUALS = ["scotch_user7.0.pdf", "ptscotch_user7.0.pdf"]

_FUNC_RE = re.compile(r"\bSCOTCH_\w+")


def walk(items, reader, pdf_name, out):
    for item in items:
        if isinstance(item, list):
            walk(item, reader, pdf_name, out)
            continue
        match = _FUNC_RE.search(item.title or "")
        if match:
            out[match.group(0)] = {
                "pdf": pdf_name,
                "page": reader.get_destination_page_number(item) + 1,
            }


def main():
    mapping = {}
    for pdf_name in MANUALS:
        path = DOC_DIR / pdf_name
        if not path.exists():
            raise SystemExit(f"Manual not found (init the scotch submodule?): {path}")
        reader = PdfReader(str(path))
        walk(reader.outline, reader, pdf_name, mapping)
    OUT_PATH.write_text(json.dumps(mapping, indent=1, sort_keys=True) + "\n")
    print(f"{len(mapping)} functions -> {OUT_PATH}")


if __name__ == "__main__":
    main()
