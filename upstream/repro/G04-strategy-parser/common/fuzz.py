import random, subprocess, sys, os
# usage: fuzz.py <st-binary> <bases.txt> <mutations-per-base> <seed>
st, basefile, nbr, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])  # argv[5] = lib dir
random.seed(seed)
alphabet = "abcdefghijklmnopqrstuvwxyz0123456789{}()[]|&!=<>+-*%/?:;,. \n\t\"'"
bases = [l.rstrip("\n").split(" ", 1) for l in open(basefile) if " " in l]
hits = {}; total = 0; crashes = 0
env = dict(os.environ, LD_LIBRARY_PATH=sys.argv[5], ASAN_OPTIONS="detect_leaks=1", UBSAN_OPTIONS="print_stacktrace=1")
for mode, base in bases:
    for i in range(nbr):
        s = list(base)
        for _ in range(random.randint(1, 3)):
            k = random.randint(0, 2)
            if k == 0 and len(s) > 1: del s[random.randrange(len(s))]
            elif k == 1: s.insert(random.randrange(len(s) + 1), random.choice(alphabet))
            else: s[random.randrange(len(s))] = random.choice(alphabet)
        s = "".join(s)
        total += 1
        p = subprocess.run([st, s, mode], capture_output=True, text=True, env=env, timeout=60)
        out = p.stdout + p.stderr
        for key in ("AddressSanitizer", "runtime error", "LeakSanitizer"):
            if key in out:
                loc = [l for l in out.splitlines() if ("#1 " in l or "runtime error" in l or "SUMMARY" in l)]
                sig = key + " " + (loc[0].split("/")[-1] if loc else "")
                hits.setdefault(sig, []).append(s)
                break
print(f"{total} mutations; {sum(len(v) for v in hits.values())} sanitizer hits")
for k, v in sorted(hits.items()): print(f"{len(v):5d}  {k}\n       e.g. {v[0]!r}")
