#!/usr/bin/env python3
# Mutation harness for Scotch "deco" target files (COR-16 / PS-COR-1).
# Runs atst and gmap (ASan+UBSan builds) on mutated deco targets and counts
# distinct sanitizer signatures. Run with: python3 -I fuzz.py <bin> <lib> <corpus> <graph> <iters> <seed>
import os, re, random, subprocess, sys

bindir, libdir, corpus, graph = sys.argv[1:5]
iters = int(sys.argv[5]) if len(sys.argv) > 5 else 300
seed = int(sys.argv[6]) if len(sys.argv) > 6 else 1
rng = random.Random(seed)
env = dict(os.environ, LD_LIBRARY_PATH=libdir,
           UBSAN_OPTIONS="print_stacktrace=1",
           ASAN_OPTIONS="allocator_may_return_null=1:detect_leaks=1:exitcode=99")
SIG = re.compile(r"(AddressSanitizer: [a-z0-9_ -]+|runtime error: [^\n]*|LeakSanitizer|SEGV)")
INTS = ["0", "1", "-1", "2", "3", "5", "7", "9", "2000000000", "70000", "-2147483648", "2147483647"]

seeds = []
for fn in sorted(os.listdir(corpus)):
    p = os.path.join(corpus, fn)
    with open(p) as f:
        seeds.append(f.read())

def mutate(txt):
    toks = txt.split()
    if not toks:
        return txt
    n = rng.randint(1, 4)
    for _ in range(n):
        i = rng.randrange(len(toks))
        if toks[i].lstrip("-").isdigit():
            toks[i] = rng.choice(INTS)
        else:
            toks[i] = rng.choice(INTS)
    # occasionally drop or duplicate a token
    if rng.random() < 0.2 and len(toks) > 3:
        del toks[rng.randrange(len(toks))]
    return " ".join(toks) + "\n"

hits = {}
for it in range(iters):
    base = rng.choice(seeds)
    data = mutate(base)
    fn = "/tmp/fuzz_cur.tgt"
    with open(fn, "w") as f:
        f.write(data)
    for prog in (["atst", fn], ["gmap", graph, fn, "/dev/null", "-vm"]):
        cmd = [os.path.join(bindir, prog[0])] + prog[1:]
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            continue
        out = r.stderr + r.stdout
        m = SIG.search(out)
        if m:
            key = (prog[0], m.group(1)[:60])
            if key not in hits:
                hits[key] = data
with open("/tmp/fuzz_hits.txt", "w") as f:
    for k, v in sorted(hits.items()):
        f.write("%s\t%s\t:: %s\n" % (k[0], k[1], v.strip().replace("\n", " / ")))
print("distinct signatures:", len(hits))
for k in sorted(hits):
    print(" ", k[0], "|", k[1])
