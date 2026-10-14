#!/usr/bin/env python3
"""Mutation fuzzer for the tleaf / ltleaf / hcub target-file loaders.
usage: python3 -I fuzz_tgt.py <archload-binary> <iterations> <seed>
Runs the archload harness (ASan+UBSan build) on mutated target strings and counts sanitizer hits."""
import os, random, subprocess, sys
binary, iters, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
random.seed(seed)
seeds = [
    "hcub 1", "hcub 4", "hcub 10", "hcub 30", "hcub 31", "hcub 32", "hcub 62", "hcub 63", "hcub 64",
    "tleaf 1 2 1", "tleaf 2 4 3 2 1", "tleaf 3 32 10 2 5 4 1", "tleaf 3 6 20 3 5 4 1",
    "ltleaf 3 32 10 2 5 4 1 8 0 2 4 6 1 3 5 7", "ltleaf 2 2 1 2 1 4 3 2 1 0", "ltleaf 1 4 1 1 0",
    "ltleaf 2 2 1 4 1 2 1 0", "sub 2 0 1 tleaf 2 4 3 2 1", "sub 1 0 tleaf 1 2 1",
]
specials = ["0", "-1", "1", "2", "3", "4", "7", "8", "31", "32", "33", "63", "64", "65",
            "65536", "46341", "2147483647", "-2147483648", "4294967296", "9223372036854775807", "99999999999999999999"]
def mutate(s):
    toks = s.split()
    for _ in range(random.randint(1, 3)):
        op = random.randint(0, 5)
        if op == 0 and len(toks) > 1:
            i = random.randrange(1, len(toks)); toks[i] = random.choice(specials)
        elif op == 1 and len(toks) > 1:
            i = random.randrange(1, len(toks)); toks[i] = str(int(toks[i]) + random.choice([-1, 1, -2, 2]) if toks[i].lstrip('-').isdigit() else toks[i])
        elif op == 2 and len(toks) > 1:
            del toks[random.randrange(1, len(toks))]
        elif op == 3:
            toks.insert(random.randrange(1, len(toks) + 1), random.choice(specials))
        elif op == 4 and len(toks) > 2:
            i, j = random.randrange(1, len(toks)), random.randrange(1, len(toks)); toks[i], toks[j] = toks[j], toks[i]
        else:
            toks = toks[:random.randrange(1, len(toks) + 1)]
    return " ".join(toks)
hits = {}
total = 0
env = dict(os.environ, UBSAN_OPTIONS="print_stacktrace=0", ASAN_OPTIONS="detect_leaks=1")
for n in range(iters):
    s = mutate(random.choice(seeds))
    total += 1
    try:
        p = subprocess.run([binary, s], capture_output=True, text=True, timeout=20, env=env)
        err = p.stderr
    except subprocess.TimeoutExpired:
        err = "TIMEOUT"
    key = None
    for line in err.splitlines():
        if "runtime error" in line or "AddressSanitizer" in line or "LeakSanitizer" in line or "TIMEOUT" in line:
            key = line.split("==")[-1].strip()[:110] if "Sanitizer" in line else line.strip()[:110]
            break
    if key:
        hits.setdefault(key, []).append(s)
print("inputs:", total, "distinct sanitizer signatures:", len(hits), "inputs with hits:", sum(len(v) for v in hits.values()))
for k, v in sorted(hits.items(), key=lambda kv: -len(kv[1])):
    print("%4d  %s\n      e.g. %r" % (len(v), k, v[0]))
