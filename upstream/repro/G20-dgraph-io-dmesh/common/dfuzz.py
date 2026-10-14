#!/usr/bin/env python3
# Distributed graph-loader mutation fuzzer.
# usage: python3 -I dfuzz.py BINDIR LIBDIR SEEDDIR OUTDIR N NP [SEED]
# Mutates .grf seeds and feeds them to ./dgload under mpirun -np NP.
import os, random, re, subprocess, sys, collections
bindir, libdir, seeddir, outdir, n, npv = sys.argv[1:7]
n = int(n); npv = int(npv)
seed = int(sys.argv[7]) if len(sys.argv) > 7 else 42
rng = random.Random(seed)
os.makedirs(os.path.join(outdir, "crashes"), exist_ok=True)
seeds = [open(os.path.join(seeddir, f), "rb").read()
         for f in sorted(os.listdir(seeddir)) if f.endswith(".grf")]
BIG = [b"-1", b"0", b"1000000", b"999999", b"9999999999", b"-8", b"2", b"-2147483648"]
def mutate(data):
    nums = [m.span() for m in re.finditer(rb'-?\d+', data)]
    for _ in range(rng.randint(1, 3)):
        c = rng.randint(0, 6)
        if c <= 3 and nums:
            s, e = rng.choice(nums); data = data[:s] + rng.choice(BIG) + data[e:]
            nums = [m.span() for m in re.finditer(rb'-?\d+', data)]
        elif c == 4 and len(data) > 8:
            data = data[:rng.randrange(4, len(data))]
        elif c == 5 and len(data) > 4:
            i = rng.randrange(len(data)); data = data[:i] + bytes([data[i]^(1<<rng.randrange(8))]) + data[i+1:]
        else:
            toks = data.split()
            if len(toks) > 1: del toks[rng.randrange(len(toks))]; data = b" ".join(toks)
    return data
FRAME = re.compile(rb'in (_?SCOTCH\w+|dgraph\w+|graph\w+)')
buckets = {}; san = 0; hang = 0
env = dict(os.environ, LD_LIBRARY_PATH=libdir,
           ASAN_OPTIONS="detect_leaks=0:abort_on_error=0:exitcode=99",
           UBSAN_OPTIONS="halt_on_error=0")
for it in range(n):
    data = mutate(rng.choice(seeds))
    path = os.path.join(outdir, "cur.grf"); open(path, "wb").write(data)
    cmd = ["mpirun", "--oversubscribe", "-np", str(npv), os.path.join(bindir, "dgload"), path]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=15, env=env); out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        out = b"TIMEOUT-HANG"; hang += 1
    if b"AddressSanitizer" in out or b"runtime error:" in out or b"TIMEOUT-HANG" in out:
        san += 1
        m = FRAME.search(out)
        key = m.group(1).decode() if m else out[:48].decode("latin1","replace")
        if b"TIMEOUT" in out: key = "HANG:" + key
        if key not in buckets:
            buckets[key] = it
            open(os.path.join(outdir, "crashes", "c%04d.grf" % it), "wb").write(data)
print("np=%d iters=%d hits=%d hangs=%d buckets=%d" % (npv, n, san, hang, len(buckets)))
for k in sorted(buckets): print("  %-50s first=%d" % (k, buckets[k]))
