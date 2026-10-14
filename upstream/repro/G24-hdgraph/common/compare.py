#!/usr/bin/env python3
# compare.py CENSUS BASE_SCAN PATCHED_SCAN : side-by-side classification of every injected allocation
import re, sys, collections
def census(fn):
    d = {}
    for line in open(fn):
        m = re.search(r'rank (\d+): alloc #(\d+) from (\S+)', line)
        if m: d[(int(m.group(1)), int(m.group(2)))] = m.group(3)
    return d
def classify(line, np_):
    m = re.match(r'nth=(\d+) exit=(\d+) :: (.*)', line)
    if not m: return None
    nth, ex, rest = int(m.group(1)), int(m.group(2)), m.group(3)
    rcs = dict(re.findall(r'rank (\d+): order rc=(\d+)|rank (\d+): arch \S+ map rc=(\d+)', rest) and [(a or c, b or d) for a, b, c, d in re.findall(r'rank (\d+): order rc=(\d+)|rank (\d+): arch \S+ map rc=(\d+)', rest)])
    live = sum(int(x) for x in re.findall(r'live scotch blocks (\d+)', rest))
    if 'failing allocation' not in rest: kind = 'not-reached'
    elif ('signal' in rest) or 'runtime error' in rest or ex in (139, 134, 136): kind = 'CRASH'
    elif 'HANG' in rest or len(rcs) < np_: kind = 'HANG'
    elif len(set(rcs.values())) > 1: kind = 'DISAGREE(' + ','.join('%s:%s' % kv for kv in sorted(rcs.items())) + ')'
    elif list(rcs.values())[0] == '1': kind = 'all-rc1'
    else: kind = 'all-rc0'
    if live: kind += ' LEAK=%d' % live
    return nth, kind
cen = census(sys.argv[1])
b, p = sys.argv[2], sys.argv[3]
rank = int(re.search(r'_r(\d+)\.txt', b).group(1)); np_ = int(re.search(r'_np(\d+)_', b).group(1))
B = dict(filter(None, (classify(l, np_) for l in open(b)))); P = dict(filter(None, (classify(l, np_) for l in open(p))))
print('== rank %d: %s vs %s' % (rank, b.split('/')[-1], p.split('/')[-1]))
tot = collections.Counter()
for nth in sorted(set(B) | set(P)):
    kb, kp = B.get(nth, '-'), P.get(nth, '-')
    fun = cen.get((rank, nth), '?')
    tot[(kb.split(' ')[0].split('(')[0], kp.split(' ')[0].split('(')[0])] += 1
    if kb != kp or 'HANG' in kp or 'CRASH' in kp or 'DISAGREE' in kp or 'LEAK' in kp:
        print('  nth=%-4d %-28s base: %-28s patched: %s' % (nth, fun, kb, kp))
print('  totals (base -> patched):', ', '.join('%s->%s:%d' % (k[0], k[1], v) for k, v in sorted(tot.items())))
