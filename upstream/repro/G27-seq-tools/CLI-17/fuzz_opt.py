#!/usr/bin/env python3 -I
# Mutation fuzzer for the gout -O option parser (C_parse in gout_c.c).
# usage: python3 -I fuzz_opt.py <gout binary> <graph> <xyz> <iterations> [seed]
import os, random, subprocess, sys, collections
gout, grf, xyz, iters = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
rnd = random.Random(seed)
seeds = ["i{c,r}", "i{g,v}", "m{e}", "m{f}", "p{d,e,g,r,s}", "p{a,e,c,d,l}", "p{c,e,d,x=0.3,X=0.6,y=0.2,Y=0.5}", "t{c,d,v}", "t{b,a,r}", "v{r}", "v{v}", "i", "m", "p", "t", "v"]
alphabet = "ivmptcgrvedfslaXxYy{},=0.9 -\\\"'"
def mutate(s):
    s = list(s)
    for _ in range(rnd.randint(1, 3)):
        op = rnd.randint(0, 3)
        if op == 0 and s: del s[rnd.randrange(len(s))]
        elif op == 1: s.insert(rnd.randint(0, len(s)), rnd.choice(alphabet))
        elif op == 2 and s: s[rnd.randrange(len(s))] = rnd.choice(alphabet)
        else: s = s[:rnd.randint(0, len(s))]
    return "".join(s)
sigs = collections.Counter(); examples = {}
env = dict(os.environ, UBSAN_OPTIONS="print_stacktrace=0", ASAN_OPTIONS="detect_leaks=0")
for i in range(iters):
    opt = mutate(rnd.choice(seeds))
    if rnd.random() < 0.3: opt = mutate(opt)
    p = subprocess.run([gout, grf, xyz, "/dev/null", "/dev/null", "-mn", "-O" + opt], env=env, capture_output=True, text=True, timeout=30)
    err = p.stderr
    key = None
    for l in err.splitlines():
        if "runtime error" in l or "AddressSanitizer" in l or "SEGV" in l:
            key = l.split(" in ")[0] if "AddressSanitizer" in l else l.split(": runtime error")[0] + ": " + l.split("runtime error: ")[1][:40]
            break
    if key is None and p.returncode not in (0, 1): key = "rc=%d" % p.returncode
    if key:
        sigs[key] += 1; examples.setdefault(key, repr(opt))
print("iterations:", iters, "distinct sanitizer/abnormal signatures:", len(sigs))
for k, v in sigs.most_common(): print(v, k, "example -O" + examples[k])
