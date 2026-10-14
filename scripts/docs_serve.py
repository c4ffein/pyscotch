#!/usr/bin/env python3
"""Serve the built docs (docs/out) locally, plus the PRIVATE upstream reports.

    docs_serve.py [--host 127.0.0.1] [--port 8080] [--no-build]

The rendered per-version reports (upstream/reports/<version>/out/) are mounted virtually at
/upstream-reports/<version>/ and are never copied into docs/out, which CI publishes to GitHub Pages.
Binding to all interfaces (--host 0.0.0.0) is an explicit opt-in: the reports describe unfixed
upstream bugs and may not be shared yet, so anyone who can reach the port can read them.
"""

import argparse
import functools
import http.server
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS_OUT = REPO / "docs" / "out"
PRIVATE = REPO / "upstream" / "reports"
MOUNT = "/upstream-reports/"


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        raw = path.split("?", 1)[0].split("#", 1)[0]
        if raw.startswith(MOUNT):
            rel = Path(*[p for p in raw[len(MOUNT) :].split("/") if p not in ("", ".", "..")])
            parts = rel.parts
            if len(parts) >= 1 and (PRIVATE / parts[0] / "out").is_dir():
                return str(PRIVATE / parts[0] / "out" / Path(*parts[1:]))
            return str(PRIVATE / "__missing__")
        return super().translate_path(path)

    def list_directory(self, path):
        self.send_error(404, "no directory listing")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-build", action="store_true", help="serve the existing docs/out")
    args = ap.parse_args()
    if not args.no_build:
        subprocess.run([sys.executable, str(REPO / "docs" / "site" / "build.py")], check=True)
    if not DOCS_OUT.is_dir():
        sys.exit("docs/out is missing: run without --no-build")
    reports = sorted(p.parent.name for p in PRIVATE.glob("*/out"))
    if args.host not in ("127.0.0.1", "localhost", "::1") and reports:
        print(
            f"WARNING: serving PRIVATE upstream reports ({', '.join(reports)}) on {args.host}:{args.port} — "
            "reachable by anyone who can reach this port. Ctrl-C if that is not what you want.",
            file=sys.stderr,
        )
    server = http.server.ThreadingHTTPServer(
        (args.host, args.port), functools.partial(Handler, directory=str(DOCS_OUT))
    )
    print(f"docs: http://{args.host}:{args.port}/")
    for v in reports:
        print(f"report {v}: http://{args.host}:{args.port}{MOUNT}{v}/report.html  (PDF: report.pdf)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
