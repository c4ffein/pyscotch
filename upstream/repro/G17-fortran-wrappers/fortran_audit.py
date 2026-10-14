#!/usr/bin/env python3
"""Audit the Fortran API of Scotch against its C API and its user's manuals.

Usage:  python3 -I fortran_audit.py <scotch source tree> [--json out.json] [--md out.md]

The script cross-checks three sources of truth:
  (1) every SCOTCH_FORTRAN / FORTRAN wrapper in src/libscotch/*_f.c and
      src/libscotchmetis/*_f.c;
  (2) every C routine of the public API (prototypes in src/libscotch/library.h
      and library_pt.h, definitions in src/libscotch/library*.c);
  (3) every Fortran synopsis in doc/src/scotch/s_l.tex and
      doc/src/ptscotch/p_l.tex, and the C synopsis next to it.

It reports, per defect class:
  CASE      wrapper's lower-case macro name is not the lower-cased upper name
  BYVALUE   wrapper parameter taken by value (not a pointer) -- except the
            hidden Fortran string length that follows a 'char *' parameter
  ORDER     wrapper forwards its parameters to the C routine in an order that
            differs from the C definition's parameter order (names compared
            after stripping '*', '&' and casts; only when the C definition
            uses the same names)
  TYPE      wrapper parameter type disagrees with the manual's declared type
            (integer -> int, integer*num -> SCOTCH_Num, integer*idx ->
            SCOTCH_Idx, doubleprecision -> double or opaque object, ...)
  IERR      C routine returns int but the wrapper has no trailing 'int *'
            parameter, or the manual lists no trailing 'integer ierr'
            (or the reverse)
  COUNT     manual's Fortran synopsis and the wrapper disagree on the number
            of (visible) arguments
  NOWRAP    manual documents a Fortran routine that no *_f.c defines
  NODOC     a wrapper exists but the manual has no Fortran synopsis for it
  DOCNAME   manual's Fortran name is not 'scotchf' + lower-cased C name
  DOCORDER  manual's Fortran argument names are not the C synopsis's names in
            the same order (object pointers 'xxxptr' -> 'xxxdat' and
            'stream' -> 'fildes' renames tolerated)
  DOCC      manual's C synopsis disagrees with library.h (arity, pointer-ness)
  DOCTYPE   manual's Fortran type token is malformed (e.g. 'integer{\\it num}')
"""

import glob
import json
import os
import re
import sys

ROOT = None

# --------------------------------------------------------------------------
# (1) Wrappers
# --------------------------------------------------------------------------

WRAP_RE = re.compile(
    r'^(?:SCOTCH_FORTRAN|FORTRAN)\s*\(\s*'
    r'(?:(?P<variant>SCOTCHMETISNAME[SF]U)\s*\(\s*)?(?P<nu>[A-Za-z0-9_]+)\s*\)?\s*,\s*'
    r'(?:SCOTCHMETISNAME[SF]L\s*\(\s*)?(?P<nl>[A-Za-z0-9_]+)\s*\)?\s*,\s*'
    r'\((?P<params>[^()]*(?:\([^()]*\)[^()]*)*)\)\s*,\s*'
    r'\((?P<args>[^()]*)\)\s*\)\s*'
    r'\{(?P<body>.*?)^\}', re.M | re.S)


def strip_comments(s):
    return re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)


def split_params(s):
    out = []
    for p in s.split(','):
        p = ' '.join(p.split())
        if not p:
            continue
        m = re.match(r'^(?P<type>.*?)\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<arr>\[[^\]]*\])?$', p)
        if not m:
            out.append({'type': p, 'name': '?', 'raw': p})
            continue
        t = m.group('type')
        if m.group('arr'):
            t = t + ' ' + m.group('arr')
        out.append({'type': t, 'name': m.group('name'), 'raw': p})
    return out


def parse_wrappers():
    wrappers = []
    files = sorted(glob.glob(os.path.join(ROOT, 'src/libscotch/*_f.c')) +
                   glob.glob(os.path.join(ROOT, 'src/libscotchmetis/*_f.c')))
    for fn in files:
        raw = open(fn).read()
        text = raw.replace('\\\n', '\n')
        text = strip_comments(text)
        for m in WRAP_RE.finditer(text):
            line = raw[:raw.find(m.group('nu') + ',')].count('\n') + 1
            params = split_params(m.group('params'))
            args = [a.strip() for a in m.group('args').split(',') if a.strip()]
            body = m.group('body')
            calls = re.findall(r'(SCOTCH_[A-Za-z0-9_]+|SCOTCHMETISNAMES\s*\([A-Za-z0-9_]+\)|_SCOTCH_[A-Za-z0-9_]+)\s*\(([^;]*?)\)\s*;', body, re.S)
            wrappers.append({
                'file': os.path.relpath(fn, ROOT), 'line': line,
                'nu': m.group('nu'), 'nl': m.group('nl'),
                'variant': m.group('variant') or 'SCOTCH_FORTRAN',
                'fname': (('scotchf' + m.group('nl')) if not m.group('variant') else m.group('nl')).lower(),
                'params': params, 'args': args, 'body': body,
                'calls': [(c[0].replace(' ', ''), [' '.join(x.split()) for x in c[1].split(',')]) for c in calls],
            })
        # Count stanzas we failed to parse
        nstanza = len(re.findall(r'^(?:SCOTCH_FORTRAN|FORTRAN)\s*\(', text, re.M))
        nfound = sum(1 for w in wrappers if w['file'] == os.path.relpath(fn, ROOT))
        if nstanza != nfound:
            print('WARNING: %s: %d stanzas, %d parsed' % (fn, nstanza, nfound), file=sys.stderr)
    return wrappers

# --------------------------------------------------------------------------
# (2) C API
# --------------------------------------------------------------------------

PROTO_RE = re.compile(r'^(?P<ret>[A-Za-z_][A-Za-z0-9_ ]*?\**)\s+(?P<name>SCOTCH_[A-Za-z0-9_]+)\s*\((?P<params>[^;]*?)\)\s*;', re.M | re.S)


def parse_protos():
    protos = {}
    for hn in ('src/libscotch/library.h', 'src/libscotch/library_pt.h'):
        text = strip_comments(open(os.path.join(ROOT, hn)).read())
        for m in PROTO_RE.finditer(text):
            name = m.group('name')
            params = [' '.join(p.split()) for p in m.group('params').split(',')]
            if params == ['void']:
                params = []
            protos[name] = {'ret': ' '.join(m.group('ret').split()), 'params': params, 'file': hn}
    return protos


DEF_RE = re.compile(r'^(?P<name>SCOTCH_[A-Za-z0-9_]+)\s*\(\s*\n(?P<params>.*?)\)\s*\n\{', re.M | re.S)


def parse_defs():
    defs = {}
    for fn in sorted(glob.glob(os.path.join(ROOT, 'src/libscotch/library*.c'))):
        if fn.endswith('_f.c'):
            continue
        text = strip_comments(open(fn).read())
        for m in DEF_RE.finditer(text):
            params = split_params(m.group('params'))
            if len(params) == 1 and params[0]['raw'] == 'void':
                params = []
            defs[m.group('name')] = {'params': params, 'file': os.path.relpath(fn, ROOT)}
    return defs

# --------------------------------------------------------------------------
# (3) Manuals
# --------------------------------------------------------------------------

SEC_RE = re.compile(r'\\subsubsection\{(?P<name>.*)\}\s*$', re.M)
TAB_RE = re.compile(r'\\(?:tt|texttt)\{?\\begin\{tabular\}\{l@\{\}ll?\}\n(?P<body>.*?)\n\\end\{tabular\}\}', re.S)


def untex(s):
    s = s.replace('\\_', '_').replace('\\lbt ', '').replace('\\lbt', '').replace('\\lbo ', '')
    s = s.replace('{\\it num}', 'num').replace('{\\it idx}', 'idx')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    return ' '.join(s.split())


def parse_tab(body):
    rows = []
    body = body.strip('\n')
    for r in body.split('\\\\'):
        parts = [untex(x) for x in r.split('&')]
        if len(parts) == 3:
            rows.append({'type': parts[1], 'name': parts[2].rstrip(') ').strip(), 'head': parts[0].strip()})
        elif len(parts) == 2:                     # Routine with no argument: 'name ( & & )' or 'name ()'
            rows.append({'type': parts[1].rstrip(') ').strip(), 'name': '', 'head': parts[0].strip()})
        elif len(parts) == 1 and parts[0].strip():
            rows.append({'type': '', 'name': '', 'head': parts[0].strip()})
    return rows


def parse_docs():
    docs = {}
    for dn in ('doc/src/scotch/s_l.tex', 'doc/src/ptscotch/p_l.tex'):
        text = open(os.path.join(ROOT, dn)).read()
        secs = list(SEC_RE.finditer(text))
        for i, sm in enumerate(secs):
            start = sm.end()
            end = secs[i + 1].start() if i + 1 < len(secs) else len(text)
            chunk = text[start:end]
            synidx = chunk.find('\\progsyn')
            desidx = chunk.find('\\progdes')
            if synidx < 0 or desidx < 0:
                continue
            syn = chunk[synidx:desidx]
            names = re.findall(r'(SCOTCH\\_[A-Za-z0-9\\_]+|METIS\\_[A-Za-z0-9\\_]+|ParMETIS\\_[A-Za-z0-9\\_]+)', sm.group('name'))
            if not names:
                continue
            cname = untex(names[0])
            allnames = [untex(n) for n in names]
            ctabs = []
            ftabs = []
            for tm in TAB_RE.finditer(syn):
                line = text[:start + synidx + tm.start()].count('\n') + 1
                rows = parse_tab(tm.group('body'))
                head = rows[0]['head'] if rows else ''
                entry = {'line': line, 'rows': rows, 'head': head, 'file': dn}
                if re.match(r'^(scotchf|metis|parmetis)', head, re.I) or re.match(r'^[a-z]+ \(', head) and not re.search(r'\bSCOTCH_', head):
                    hm = re.match(r'^(?P<fname>[A-Za-z0-9_]+)\s*\(', head)
                    entry['fname'] = hm.group('fname') if hm else head
                    args = []
                    for r in rows:
                        if r['name'] or r['type']:
                            args.append({'type': r['type'], 'name': r['name']})
                    entry['args'] = args
                    ftabs.append(entry)
                else:
                    hm = re.match(r'^(?P<ret>.*?)\s*(?P<cn>SCOTCH_[A-Za-z0-9_]+)\s*\(', head)
                    if hm:
                        entry['cname'] = hm.group('cn')
                        entry['ret'] = hm.group('ret')
                        args = []
                        for r in rows:
                            if r['name'] or r['type']:
                                args.append({'type': r['type'], 'name': r['name']})
                        entry['args'] = args
                        ctabs.append(entry)
            docs.setdefault(cname, []).append({'file': dn, 'line': text[:sm.start()].count('\n') + 1, 'ctabs': ctabs, 'ftabs': ftabs, 'names': allnames})
    return docs

# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

FTYPE_MAP = {
    'integer': ('int',),
    'integer*num': ('SCOTCH_Num', 'SCOTCH_GraphPart2'),
    'integer*num (*)': ('SCOTCH_Num', 'SCOTCH_GraphPart2'),
    'integer*idx': ('SCOTCH_Idx',),
    'integer*idx (*)': ('SCOTCH_Idx',),
    'doubleprecision': ('double',),
    'doubleprecision (*)': ('double', 'SCOTCH_Arch', 'SCOTCH_ArchDom', 'SCOTCH_Context', 'SCOTCH_Geom', 'SCOTCH_Graph',
                            'SCOTCH_Mapping', 'SCOTCH_Mesh', 'SCOTCH_Ordering', 'SCOTCH_Strat', 'SCOTCH_Dgraph',
                            'SCOTCH_Dmapping', 'SCOTCH_Dordering', 'SCOTCH_Dmesh', 'SCOTCH_DgraphHaloReq'),
    'character (*)': ('char',),
    'integer*1': ('SCOTCH_GraphPart2',),
    'integer*1 (*)': ('SCOTCH_GraphPart2',),
    'integer*num (**)': ('SCOTCH_Num',),             # METIS routines returning allocated arrays
    'float (*)': ('float', 'double'),                # ParMETIS real_t arrays
}


def base_ctype(t):
    t = re.sub(r'\b(const|restrict|volatile)\b', '', t)
    t = t.replace('*', ' ').replace('[256]', ' ')
    t = re.sub(r'\[[^\]]*\]', ' ', t)
    return ' '.join(t.split())


def is_pointer(t):
    return '*' in t or '[' in t


def strip_arg(a):
    a = re.sub(r'\([^)]*\)', '', a)               # Casts
    a = a.strip().lstrip('*&').strip()
    return a


def run():
    wrappers = parse_wrappers()
    protos = parse_protos()
    defs = parse_defs()
    docs = parse_docs()

    findings = []

    def add(cls, where, what, **kw):
        d = {'class': cls, 'where': where, 'what': what}
        d.update(kw)
        findings.append(d)

    # Index wrappers by lower name and by C target
    wrap_by_nl = {}
    for w in wrappers:
        if w['variant'] == 'SCOTCHMETISNAMESU':      # Scotch-prefixed METIS entry points (with ierr) are not documented
            continue
        wrap_by_nl[w['fname']] = w

    # Index doc Fortran synopses
    doc_f = {}                                    # fortran name -> (cname, entry, sec)
    for cname, secs in docs.items():
        for sec in secs:
            for ft in sec['ftabs']:
                doc_f.setdefault(ft['fname'].lower(), []).append((cname, ft, sec))

    # ---- Per-wrapper checks
    for w in wrappers:
        where = '%s:%d' % (w['file'], w['line'])
        tag = w['nl']
        # CASE
        if w['nl'] != w['nu'].lower() or w['nl'] != w['nl'].lower() or w['nu'] != w['nu'].upper():
            add('CASE', where, "macro names '%s' / '%s' do not agree" % (w['nu'], w['nl']), wrapper=tag)
        # BYVALUE
        prev_char = False
        for i, p in enumerate(w['params']):
            t = p['type']
            if not is_pointer(t) and p['raw'] != 'void':
                hidden = (base_ctype(t) == 'int' and p['name'].endswith('nbr') and
                          any('char' in q['type'] for q in w['params'][:i]))
                if not hidden:
                    add('BYVALUE', where, "parameter '%s' taken by value (%s)" % (p['name'], p['raw']), wrapper=tag)
        # Determine the C target
        target = None
        for cn, cargs in w['calls']:
            if cn.startswith('SCOTCH_NAME_') or cn.startswith('SCOTCH_errorPrint'):
                continue
            if cn.startswith('SCOTCH_') or cn.startswith('SCOTCHMETISNAMES'):
                target = (cn, cargs)
                break
        w['target'] = target[0] if target else ''
        # IERR (wrapper side): C returns int -> last param must be int * revaptr
        if target and target[0] in protos:
            ret = protos[target[0]]['ret']
            last = w['params'][-1] if w['params'] else None
            visible = [p for p in w['params'] if not (not is_pointer(p['type']) and base_ctype(p['type']) == 'int')]
            lastv = visible[-1] if visible else None
            has_reva = lastv is not None and base_ctype(lastv['type']) == 'int' and is_pointer(lastv['type']) and lastv['name'].startswith('reva')
            valret = re.search(r'=\s*' + re.escape(target[0].split('(')[0]) + r'\s*\(', w['body']) is not None and not has_reva
            if ret == 'int' and not has_reva and not valret and w['variant'] != 'SCOTCHMETISNAMEFU':
                add('IERR', where, "C routine %s returns int but wrapper has no trailing 'int * revaptr' (last: %s)" % (target[0], lastv['raw'] if lastv else '-'), wrapper=tag)
            if ret == 'void' and has_reva:
                add('IERR', where, "C routine %s returns void but wrapper has a trailing 'int * revaptr'" % target[0], wrapper=tag)
            # ORDER: call args vs C definition's parameter names
            if target[0] in defs:
                w['order_checked'] = 'strong'
                dnames = [p['name'] for p in defs[target[0]]['params']]
                cargs = [strip_arg(a) for a in target[1] if a.strip()]
                if len(cargs) != len(dnames):
                    add('ORDER', where, "wrapper calls %s with %d args, C definition has %d" % (target[0], len(cargs), len(dnames)), wrapper=tag)
                elif sorted(cargs) != sorted(dnames):
                    w['order_checked'] = 'declaration-order only'
                elif cargs != dnames:
                    add('ORDER', where, "wrapper calls %s (%s) but C definition order is (%s)" % (target[0], ', '.join(cargs), ', '.join(dnames)), wrapper=tag)
                if True:
                    # Also check: wrapper passes its own parameters in declaration order
                    pnames = [p['name'] for p in w['params']]
                    own = [a for a in cargs if a in pnames]
                    ownord = [p for p in pnames if p in own]
                    if own != ownord:
                        add('ORDER', where, "wrapper forwards its parameters out of declaration order: call (%s), params (%s)" % (', '.join(own), ', '.join(ownord)), wrapper=tag)
        # CTYPE: forwarded parameters must have the C definition's base type; RETTYPE: value stored in the right type
        if target and target[0] in defs:
            dparams = defs[target[0]]['params']
            cargs = [a for a in target[1] if a.strip()]
            pbyname = dict((p['name'], p) for p in w['params'])
            if len(cargs) == len(dparams):
                for a, dp in zip(cargs, dparams):
                    nm = strip_arg(a)
                    if nm in pbyname:
                        wb = base_ctype(pbyname[nm]['type'])
                        cb = base_ctype(dp['type'])
                        if wb != cb and not (wb == 'void' or cb == 'void') and not (wb == 'MPI_Fint') and not (set((wb, cb)) == set(('Gnum', 'SCOTCH_Num'))):
                            add('CTYPE', where, "parameter '%s' is '%s' in the wrapper but '%s' in %s" % (nm, pbyname[nm]['raw'], dp['raw'], target[0]), wrapper=tag)
        if target and target[0] in protos:
            m2 = re.search(r'\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*' + re.escape(target[0]) + r'\s*\(', w['body'])
            if m2 and m2.group(1) in dict((p['name'], p) for p in w['params']):
                pt = base_ctype(dict((p['name'], p) for p in w['params'])[m2.group(1)]['type'])
                rt = base_ctype(protos[target[0]]['ret'])
                if pt != rt:
                    add('RETTYPE', where, "result of %s (returns %s) stored through '%s'" % (target[0], protos[target[0]]['ret'], dict((p['name'], p) for p in w['params'])[m2.group(1)]['raw']), wrapper=tag)
        # NODOC + TYPE + COUNT
        dl = doc_f.get(w['fname']) if w['variant'] != 'SCOTCHMETISNAMESU' else None
        if not dl:
            if w['variant'] != 'SCOTCHMETISNAMESU':
                csec = target[0] in docs if target else False
                add('NODOC', where, "wrapper '%s' has no Fortran synopsis in the manuals (%s)" % (w['nl'], ('C routine %s has a section' % target[0]) if csec else 'C routine not documented either'), wrapper=tag, csec=csec)
        else:
            for cname, ft, sec in dl:
                dwhere = '%s:%d' % (ft['file'], ft['line'])
                visible = [p for p in w['params'] if not (not is_pointer(p['type']) and base_ctype(p['type']) == 'int') and p['raw'] != 'void']
                if len(visible) != len(ft['args']):
                    add('COUNT', where, "wrapper has %d visible parameters, manual (%s) lists %d" % (len(visible), dwhere, len(ft['args'])), wrapper=tag, doc=dwhere)
                for p, a in zip(visible, ft['args']):
                    dt = a['type']
                    if dt not in FTYPE_MAP:
                        add('DOCTYPE', dwhere, "malformed Fortran type '%s' for argument '%s'" % (dt, a['name']), wrapper=tag)
                        continue
                    bt = base_ctype(p['type'])
                    ok = FTYPE_MAP[dt]
                    if bt == 'MPI_Fint' and dt == 'integer':
                        continue
                    if bt == 'void' and dt == 'doubleprecision (*)': # Untyped data buffer
                        continue
                    if bt not in ok:
                        add('TYPE', where, "parameter '%s' is '%s' in the wrapper but '%s %s' in the manual (%s)" % (p['name'], p['raw'], dt, a['name'], dwhere), wrapper=tag, doc=dwhere)
                # IERR (doc side)
                if target and target[0] in protos:
                    ret = protos[target[0]]['ret']
                    dlast = ft['args'][-1] if ft['args'] else None
                    dierr = dlast is not None and dlast['type'] == 'integer' and dlast['name'] == 'ierr'
                    if ret == 'int' and not dierr and not valret and w['variant'] != 'SCOTCHMETISNAMEFU':
                        add('IERR', dwhere, "manual lists no trailing 'integer ierr' for %s (C returns int)" % ft['fname'], wrapper=tag)
                    if ret == 'void' and dierr:
                        add('IERR', dwhere, "manual lists a trailing 'integer ierr' for %s but C returns void" % ft['fname'], wrapper=tag)

    # ---- Per-doc checks
    for cname, secs in docs.items():
        for sec in secs:
            for ft in sec['ftabs']:
                dwhere = '%s:%d' % (ft['file'], ft['line'])
                fn = ft['fname'].lower()
                exps = ['scotchf' + n.replace('SCOTCH_', '').lower() for n in sec['names']]
                exp = exps[0]
                if fn not in exps and not fn.startswith('metis') and not fn.startswith('parmetis'):
                    add('DOCNAME', dwhere, "Fortran synopsis is named '%s' in section %s (expected '%s')" % (ft['fname'], cname, exp), doc=dwhere)
                if fn not in wrap_by_nl:
                    add('NOWRAP', dwhere, "manual documents '%s' (section %s) but no *_f.c defines it" % (ft['fname'], cname), doc=dwhere, cname=cname)
                for a in ft['args']:
                    if a['type'] not in FTYPE_MAP and a['type'] not in ('',):
                        if not any(f['class'] == 'DOCTYPE' and f['where'] == dwhere and a['name'] in f['what'] for f in findings):
                            add('DOCTYPE', dwhere, "malformed Fortran type '%s' for argument '%s'" % (a['type'], a['name']), doc=dwhere)
                # DOCORDER: Fortran names vs C synopsis names
                if sec['ctabs']:
                    ct = sec['ctabs'][0]
                    cnames = [a['name'] for a in ct['args']]
                    fnames = [a['name'] for a in ft['args']]
                    if fnames and fnames[-1] == 'ierr':
                        fnames = fnames[:-1]
                    # Tolerated renames
                    def norm(n):
                        n = n.rstrip(',) ')
                        n = re.sub(r'(ptr|dat|tab|val|idx|nbr|ptz)$', '', n)
                        return n
                    cn2 = [norm(x) for x in cnames]
                    fn2 = [norm(x) for x in fnames]
                    if ct.get('ret', '').strip() not in ('void', '') and ct.get('ret', '').strip() != 'int':
                        # Value-returning routine: Fortran has one extra output parameter at the end
                        if len(fn2) == len(cn2) + 1:
                            fn2 = fn2[:-1]
                    if len(fn2) != len(cn2):
                        common = [x for x in fn2 if x in cn2]
                        commonc = [x for x in cn2 if x in fn2]
                        if len(common) >= 2 and sorted(common) == sorted(commonc) and common != commonc:
                            add('DOCORDER', dwhere, "Fortran synopsis order (%s) differs from C synopsis order (%s)" % (', '.join(fnames), ', '.join(cnames)), doc=dwhere)
                    else:
                        mism = [(c, f) for c, f in zip(cn2, fn2) if c != f and not (c == 'stream' and f == 'fildes') and not (c.endswith('stream') and f.endswith('fildes'))]
                        if mism:
                            if sorted(cn2) == sorted(fn2):
                                add('DOCORDER', dwhere, "Fortran synopsis order (%s) differs from C synopsis order (%s)" % (', '.join(fnames), ', '.join(cnames)), doc=dwhere)
                            else:
                                common = [x for x in fn2 if x in cn2]
                                commonc = [x for x in cn2 if x in fn2]
                                if len(common) >= 2 and sorted(common) == sorted(commonc) and common != commonc:
                                    add('DOCORDER', dwhere, "Fortran synopsis order (%s) differs from C synopsis order (%s)" % (', '.join(fnames), ', '.join(cnames)), doc=dwhere)
            # DOCC: C synopsis vs library.h
            for ct in sec['ctabs']:
                dwhere = '%s:%d' % (ct['file'], ct['line'])
                cn = ct['cname']
                if cn not in protos:
                    add('DOCC', dwhere, "C synopsis names %s, which is not in library.h / library_pt.h" % cn, doc=dwhere)
                    continue
                pp = protos[cn]['params']
                if len(pp) != len(ct['args']):
                    add('DOCC', dwhere, "C synopsis of %s has %d args, library.h has %d" % (cn, len(ct['args']), len(pp)), doc=dwhere)
                else:
                    for i, (a, p) in enumerate(zip(ct['args'], pp)):
                        if is_pointer(p) != is_pointer(a['type']):
                            add('DOCC', dwhere, "C synopsis of %s arg %d '%s %s' vs library.h '%s'" % (cn, i + 1, a['type'], a['name'], p), doc=dwhere)
                if ct.get('ret', '').strip() and ' '.join(ct['ret'].split()) != protos[cn]['ret']:
                    add('DOCC', dwhere, "C synopsis of %s returns '%s', library.h says '%s'" % (cn, ct['ret'], protos[cn]['ret']), doc=dwhere)

    # ---- C routines without any Fortran twin (informational)
    missing_twin = []
    targets = set(w['target'] for w in wrappers)
    for cn, p in sorted(protos.items()):
        if cn not in targets:
            missing_twin.append(cn)

    return wrappers, protos, defs, docs, findings, missing_twin


def main():
    global ROOT
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    ROOT = args[0]
    jout = mdout = None
    if '--json' in args:
        jout = args[args.index('--json') + 1]
    if '--md' in args:
        mdout = args[args.index('--md') + 1]
    wrappers, protos, defs, docs, findings, missing_twin = run()
    order = ['CASE', 'BYVALUE', 'ORDER', 'CTYPE', 'RETTYPE', 'TYPE', 'IERR', 'COUNT', 'NOWRAP', 'NODOC', 'DOCNAME', 'DOCORDER', 'DOCC', 'DOCTYPE']
    findings.sort(key=lambda f: (order.index(f['class']) if f['class'] in order else 99, f['where']))
    nf = len([w for w in wrappers])
    ndoc = sum(len(ft) for secs in docs.values() for sec in secs for ft in [sec['ftabs']])
    lines = []
    lines.append('# Fortran API audit of %s' % ROOT)
    lines.append('')
    lines.append('%d wrappers in *_f.c, %d C prototypes, %d C definitions, %d documented Fortran synopses, %d findings' % (nf, len(protos), len(defs), ndoc, len(findings)))
    lines.append('')
    oc = {}
    for w in wrappers:
        oc[w.get('order_checked', 'no C definition found')] = oc.get(w.get('order_checked', 'no C definition found'), 0) + 1
    lines.append('ORDER check coverage: %s' % ', '.join('%s: %d' % kv for kv in sorted(oc.items())))
    lines.append('')
    lines.append('| class | where | what |')
    lines.append('|---|---|---|')
    for f in findings:
        lines.append('| %s | %s | %s |' % (f['class'], f['where'], f['what'].replace('|', '\\|')))
    lines.append('')
    lines.append('## C routines with no Fortran wrapper at all (informational)')
    lines.append('')
    for cn in missing_twin:
        lines.append('- %s (%s)' % (cn, protos[cn]['file']))
    lines.append('')
    lines.append('## Wrapper inventory')
    lines.append('')
    lines.append('| wrapper | file:line | C target | params |')
    lines.append('|---|---|---|---|')
    for w in wrappers:
        lines.append('| %s | %s:%d | %s | %s |' % (w['nl'], w['file'], w['line'], w['target'], '; '.join(p['raw'] for p in w['params']).replace('|', '\\|')))
    md = '\n'.join(lines) + '\n'
    if mdout:
        open(mdout, 'w').write(md)
    else:
        sys.stdout.write(md)
    if jout:
        json.dump({'findings': findings, 'missing_twin': missing_twin,
                   'wrappers': [{k: v for k, v in w.items() if k != 'body'} for w in wrappers]},
                  open(jout, 'w'), indent=1)
    sys.stderr.write('%d findings\n' % len(findings))


if __name__ == '__main__':
    main()
