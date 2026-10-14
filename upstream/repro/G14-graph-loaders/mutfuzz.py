#!/usr/bin/env python3
# Deterministic mutation fuzzer for the Scotch graph file loaders.
# usage: python3 -I mutfuzz.py BINDIR LIBDIR SEEDDIR OUTDIR N [SEED]
# Same (N, SEED) gives identical mutants, so before/after on two builds is exact.
import os, random, re, subprocess, sys, collections

bindir, libdir, seeddir, outdir, n = sys.argv[1:6]
n = int(n)
seed = int(sys.argv[6]) if len(sys.argv) > 6 else 1234
rng = random.Random(seed)
os.makedirs(os.path.join(outdir, "crashes"), exist_ok=True)

seeds = collections.defaultdict(list)
for f in sorted(os.listdir(seeddir)):
    ext = f.rsplit(".", 1)[-1]
    if ext in ("grf", "chac", "mtx", "rsa"):
        seeds[ext].append(open(os.path.join(seeddir, f), "rb").read())
exts = [e for e in ("grf", "chac", "mtx", "rsa") if seeds[e]]

CMD = {"grf":  ["{bin}/gtst", "{f}"],
       "chac": ["{bin}/gcv", "-ic", "{f}", "/dev/null"],
       "mtx":  ["{bin}/gcv", "-im", "{f}", "/dev/null"],
       "rsa":  ["{bin}/gcv", "-ib", "{f}", "/dev/null"]}
BIG = [b"-1", b"0", b"2147483647", b"999999", b"9999999999", b"2"]

def mutate(data):
    nums = [m.span() for m in re.finditer(rb'-?\d+', data)]
    k = rng.randint(1, 3)
    for _ in range(k):
        choice = rng.randint(0, 6)
        if choice <= 2 and nums:                  # replace a number
            s, e = rng.choice(nums)
            data = data[:s] + rng.choice(BIG) + data[e:]
            nums = [m.span() for m in re.finditer(rb'-?\d+', data)]
        elif choice == 3 and len(data) > 4:       # byte flip
            i = rng.randrange(len(data))
            data = data[:i] + bytes([data[i] ^ (1 << rng.randrange(8))]) + data[i+1:]
        elif choice == 4 and len(data) > 8:        # truncate
            data = data[:rng.randrange(4, len(data))]
        elif choice == 5:                          # duplicate a line
            ls = data.split(b"\n")
            if len(ls) > 1:
                i = rng.randrange(len(ls)); ls.insert(i, ls[i]); data = b"\n".join(ls)
        else:                                      # delete a token
            toks = data.split()
            if len(toks) > 1:
                del toks[rng.randrange(len(toks))]; data = b" ".join(toks)
    return data

FRAME = re.compile(rb'in (_SCOTCH\w+|SCOTCH_\w+|\w+GeomLoad\w+|\w+Load\d?) ')
buckets = {}
san = 0
for it in range(n):
    ext = exts[it % len(exts)]
    data = mutate(rng.choice(seeds[ext]))
    path = os.path.join(outdir, "cur." + ext)
    open(path, "wb").write(data)
    env = dict(os.environ, LD_LIBRARY_PATH=libdir,
               ASAN_OPTIONS="detect_leaks=0:abort_on_error=0:exitcode=99",
               UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=0")
    cmd = [c.format(bin=bindir, f=path) for c in CMD[ext]]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=10, env=env)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        out = b"TIMEOUT"; p = None
    if b"AddressSanitizer" in out or b"UndefinedBehaviorSanitizer" in out or b"runtime error:" in out or out == b"TIMEOUT":
        san += 1
        m = FRAME.search(out)
        key = (ext, m.group(1).decode() if m else out[:40].decode("latin1"))
        if key not in buckets:
            buckets[key] = it
            open(os.path.join(outdir, "crashes", "c%04d.%s" % (it, ext)), "wb").write(data)
print("iters=%d sanitizer_hits=%d unique_buckets=%d" % (n, san, len(buckets)))
for k in sorted(buckets): print("  %-6s %-40s first_iter=%d" % (k[0], k[1], buckets[k]))
