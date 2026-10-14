#!/usr/bin/env python3
# summarize.py CENSUS SCANFILE... : classify every injected allocation of a scan
import re, sys, collections
census = {}
for line in open(sys.argv[1]):
    m = re.search(r'rank (\d+): alloc #(\d+) from (\S+)', line)
    if m: census[(int(m.group(1)), int(m.group(2)))] = m.group(3)
for fn in sys.argv[2:]:
    rank = int(re.search(r'_r(\d+)\.txt', fn).group(1))
    np_ = int(re.search(r'_np(\d+)_', fn).group(1))
    cls = collections.OrderedDict()
    for line in open(fn):
        m = re.match(r'nth=(\d+) exit=(\d+) :: (.*)', line)
        if not m: continue
        nth, ex, rest = int(m.group(1)), int(m.group(2)), m.group(3)
        fun = census.get((rank, nth), '?')
        rcs = dict(re.findall(r'rank (\d+): order rc=(\d+)', rest))
        hang = 'HANG' in rest
        crash = ('signal' in rest) or ex in (139, 134, 136) or 'runtime error' in rest or 'Segmentation' in rest
        if 'failing allocation' not in rest: kind = 'not-reached'
        elif crash: kind = 'CRASH'
        elif hang: kind = 'HANG'
        elif len(rcs) < np_: kind = 'HANG(noreport)'
        elif len(set(rcs.values())) > 1: kind = 'DISAGREE'
        elif list(rcs.values())[0] == '1': kind = 'ok(all rc=1)'
        else: kind = 'ok(all rc=0?)'
        cls.setdefault(fun, []).append((nth, kind))
    print('==', fn.split('/')[-1])
    for fun, lst in cls.items():
        kinds = collections.Counter(k for _, k in lst)
        print('  %-32s %s' % (fun, ', '.join('%s:%d' % kv for kv in kinds.items())), '  nth=' + ','.join(str(n) for n, k in lst if k not in ('ok(all rc=1)', 'not-reached')))
