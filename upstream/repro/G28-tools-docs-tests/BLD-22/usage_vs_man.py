#!/usr/bin/env python3
"""Compare the option tables of the Scotch tools (their `-h` usage text, dumped
by dump_usage.sh into usage/<tool>.txt) with the man page sources
(man/man1/<page>.1.txt, OPTIONS section) and with the user's manuals
(doc/src/scotch/s_p.tex, doc/src/ptscotch/p_p.tex, \\iteme[...-x...] entries).

Usage: python3 -I usage_vs_man.py <scotch tree> <usage dir>
Exit status is 1 when any mismatch is found.
"""
import os
import re
import sys

# Tool -> man page that documents it (NAME line of the .1.txt).
MAN_ALIAS = {
    "gpart": ["gmap"], "dgpart": ["dgmap"], "dggath": ["dgscat"], "gscat": ["dgscat"],
    "amk_fft2": ["amk_ccc"], "amk_hy": ["amk_ccc"], "amk_m2": ["amk_ccc"], "amk_p2": ["amk_ccc"],
    "gmk_m2": ["gmk_m2", "gmk_hy"], "gmk_m3": ["gmk_m2", "gmk_hy"], "gmk_ub2": ["gmk_hy"],
    "mmk_m3": ["mmk_m2"],
}
# Tool -> (tex file, subsubsection title) in the user's manuals.
TEX_SECTION = {
    "gpart": "gmap", "dgpart": "dgmap", "dggath": "dgscat", "gscat": "dgscat",
    "amk_fft2": "amk\\_", "amk_hy": "amk\\_", "amk_m2": "amk\\_", "amk_p2": "amk\\_", "amk_ccc": "amk\\_",
    "gmk_m3": "gmk\\_", "gmk_ub2": "gmk\\_", "gmk_m2": "gmk\\_", "gmk_hy": "gmk\\_",
    "mmk_m3": "mmk\\_", "mmk_m2": "mmk\\_",
}
# Options that are compiled in only with SCOTCH_DEBUG_ALL (never in released binaries).
DEBUG_ONLY = {"d"}
NOT_INSTALLED = {"adm2dgr"}


def usage_keys(path):
    """Option keys of a usage dump: text between '-' and the first '<' or space."""
    keys = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^\s+-(\S+?)(<[^>]*>)?\s*:\s*(.*)$", line)
        if m:
            keys[m.group(1)] = line.strip()
    return keys


def man_keys(path):
    keys = {}
    inopt = False
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("OPTIONS"):
            inopt = True
            continue
        if re.match(r"^[A-Z][A-Z ]*$", line.rstrip("\n")):
            inopt = False
        if inopt:
            m = re.match(r"^  -(\S+)", line)
            if m:
                keys.setdefault(m.group(1), []).append(line.rstrip("\n"))
    return keys


def tex_sections(path):
    """Map subsubsection title (first program name) -> list of top-level option tokens."""
    secs = {}
    cur = None
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^\\subsubsection\{(?:\\texttt\{|\{\\tt )([^}]*)\}", line)
        if m:
            cur = m.group(1)
            secs[cur] = []
            continue
        if cur is None:
            continue
        m = re.match(r"^\\iteme\[\{?(?:\\texttt\{|\{\\tt )-([^}{\\]*)", line)
        if m:
            secs[cur].append(m.group(1).strip())
    return secs


def match_key(key, ukeys):
    """Usage key documented by a man/tex token: longest case-sensitive prefix,
    else longest case-insensitive prefix (the tools accept both cases), else
    same first letter (a doc entry such as gout's -o covers usage lines -Oi, -Om...)."""
    for test in (lambda u: key.startswith(u),
                 lambda u: key.lower().startswith(u.lower()),
                 lambda u: key[0].lower() == u[0].lower()):
        best = None
        for u in ukeys:
            if test(u) and (best is None or len(u) > len(best)):
                best = u
        if best is not None:
            return best
    return None


def compare(label, dkeys, ukeys, dups=None):
    bad = 0
    matched = set()
    for dk in dkeys:
        u = match_key(dk, ukeys)
        if u is None:
            print("   %s entry not in usage : -%s" % (label, dk))
            bad += 1
        else:
            matched.add(u)
    for m in list(matched):                       # A doc entry covers all usage lines of its option letter (gout -o: -Oi, -Om...)
        for u in ukeys:
            if len(u) > 1 and u[0].lower() == m[0].lower():
                matched.add(u)
    for dk, n in (dups or {}).items():
        if n > 1:
            print("   %s entry duplicated   : -%s (%d times)" % (label, dk, n))
            bad += 1
    for u in sorted(ukeys):
        if u not in matched:
            print("   usage option not in %s: %s" % (label, ukeys[u]))
            bad += 1
    return bad


def main():
    tree, udir = sys.argv[1], sys.argv[2]
    mandir = os.path.join(tree, "man", "man1")
    tex = {}
    for f in ("doc/src/scotch/s_p.tex", "doc/src/ptscotch/p_p.tex"):
        tex.update(tex_sections(os.path.join(tree, f)))
    pages = {}                                    # man page -> union of usage keys of the tools it documents
    secs = {}                                     # manual section -> union of usage keys
    for f in sorted(os.listdir(udir)):
        tool = f[:-4]
        if tool in NOT_INSTALLED:
            continue
        ukeys = usage_keys(os.path.join(udir, f))
        ukeys = {k: v for k, v in ukeys.items() if k not in DEBUG_ONLY}
        for page in MAN_ALIAS.get(tool, [tool]):
            pages.setdefault(page, {}).update(ukeys)
        secs.setdefault(TEX_SECTION.get(tool, tool.replace("_", "\\_")), {}).update(ukeys)
    bad = 0
    for page in sorted(pages):
        print("== man page %s.1.txt" % page)
        mpath = os.path.join(mandir, page + ".1.txt")
        if not os.path.exists(mpath):
            print("   NO MAN PAGE")
            bad += 1
            continue
        mkeys = man_keys(mpath)
        bad += compare("man", mkeys, pages[page], {k: len(v) for k, v in mkeys.items()})
    for sec in sorted(secs):
        print("== manual section %s" % sec)
        tkeys = None
        for name, opts in tex.items():
            if name == sec or name.startswith(sec + " ") or name.startswith(sec + "}"):
                tkeys = opts
                break
        if tkeys is None:
            print("   NO MANUAL SECTION")
            bad += 1
            continue
        bad += compare("manual", tkeys, secs[sec])
    print("mismatches: %d" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
