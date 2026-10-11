#!/usr/bin/env python3
"""Corpus generator for the RD-parser differential fuzzer.

Emits one strategy string per line (never containing a newline; the
newline-bearing cases live in differ.c's built-in corpus):

  1. a hand-written corpus of valid, degenerate and adversarial strings;
  2. seed strings read from files given with --seeds (typically the output
     of ./dump, upstream's own generated default strategies);
  3. --count random mutations/recombinations of all of the above,
     deterministic under --seed.

Usage:  ./dump > seeds.txt
        python3 gen.py --seeds seeds.txt --count 20000 --seed 42 | ./differ
"""

import argparse
import random
import sys

CORPUS = [
    # basics and degenerate shapes
    "",
    " ",
    "\t",
    "m",
    "r",
    "n",
    "c",
    "b",
    "f",
    "g",
    "h",
    "s",
    "d",
    "x",
    "z",
    "q",
    "9",
    "gf",
    "  m ",
    "(m)",
    "((m))",
    "(((m)))",
    "m|r",
    "|m",
    "m|",
    "|",
    "m|r|b",
    "(m|r)f",
    "m(r)",
    "mm",
    "m m",
    "(|)",
    "()",
    "(",
    ")",
    ";",
    "?",
    ":",
    ",",
    "=",
    "{",
    "}",
    "/",
    "!",
    "&",
    "<",
    ">",
    "+",
    "-",
    "*",
    "%",
    # parameter lists
    "r{sep=gf}",
    "r{sep=(gf)}",
    "r{sep=}",
    "r{sep=|}",
    "r{sep=f|g}",
    "m{asc=,low=}",
    "m{asc=b}",
    "m{ asc = b , low = h }",
    "m{asc=b,low=h}",
    "m{}",
    "m{,}",
    "m{asc}",
    "m{asc=b",
    "m{asc=b,}",
    "m{zzz=1}",
    "m{asc=$}",
    "r{sepx=g}",
    "r{SEP=gf}",
    "R{sep=gf}",
    "r{job=t}",
    "r{job=T}",
    "r{job=q}",
    "r{job=t,map=t,poli=S,bal=0.05}",
    "r{job=t,map=t,poli=s,bal=0.05,sep=gf}",
    "b{bnd=f,org=f}",
    "b{width=3}",
    "b{bnd=(f)}",
    # numeric values
    "f{move=80}",
    "f{move=-80}",
    "f{move=+80}",
    "f{move=80.9}",
    "f{move=}",
    "f{move=0x10}",
    "f{move=1e3}",
    "f{move=1e}",
    "f{move=1e+}",
    "f{move=1E+2}",
    "f{move=--5}",
    "f{move=- 5}",
    "f{move=5.}",
    "f{move=.5}",
    "f{move=999999999999999999999}",
    "f{bal=0.1}",
    "f{bal=-0.1}",
    "f{bal=+0.1}",
    "f{bal=.1}",
    "f{bal=1e-2}",
    "f{bal=}",
    "f{bal=zz}",
    "f{bal=0.0.1}",
    "f{bal=0..1}",
    # conditions
    "/vert<1000?m;",
    "/vert<1000?m:r;",
    "/vert>1000?m:r;",
    "/vert=1000?m;",
    "/(vert<1000)?m;",
    "/((vert<1000))?m;",
    "/(vert)<1000?m;",
    "/vert<1000&edge>3?m;",
    "/vert<3|edge<4?m;",
    "/!(vert<1000)?m;",
    "/!vert<1000?m;",
    "/!!vert<1000?m;",
    "/vert?m;",
    "/1<2?m;",
    "/-1<2?m;",
    "/+1<2?m;",
    "/1<-2?m;",
    "/vert%2=0?m;",
    "/(vert+2)*3<edge?m;",
    "/vert*edge<10000?m;",
    "/vert-2>0?m;",
    "/vert+2-3<4?m;",
    "/3-vert<0?m;",
    "/vert<3?;",
    "/vert<3?:;",
    "/vert<3?m",
    "/vert<3?m:;",
    "/vert<3?m:r",
    "/?m;",
    "/;",
    "/vert<3;",
    "/vert<3?m;;",
    "/vert<3?m;r",
    "/vert<edge?m:r;",
    "/load<1000?m;",
    "/load0<load?m;",
    "/levl<3?m;",
    "/zzz<3?m;",
    "/vert<3.5?m;",
    "/vert<3e2?m;",
    "/(1<2)&(3<4)?m;",
    "/(1<2)|(3<4)?m;",
    "/(1<2)+3<4?m;",
    "/1<2<3?m;",
    "/(vert<3)<4?m;",
    "/vert<(edge)?m;",
    "/vert<(edge+1)?m;",
    "/vert<edge+1?m;",
    "/(vert<3)?(m|r):((f));",
    "/vert<3?/edge<4?m;:r;;",
    # nesting and recursion
    "m{asc=f{move=200},low=r{sep=gf},vert=120,rat=0.8}",
    "m{asc=f{move=200,pass=1000,bal=0.9},low=r{job=t,map=t,poli=S,bal=0.9},vert=120,rat=0.8}",
    "n{sep=m,ole=s,ose=g}",
    "n{sep=/vert>120?m;,ole=s,ose=g}",
    "n{sep=(m|m),ole=s,ose=s}",
    "c{}",
    "d{pass=3}",
    "g{pass=3}",
    "f{cmin=0,cmax=100000,frat=0.08}",
    # strings (kept short: upstream's copy into method data is unbounded)
    's{strat="abc"}',
    'u{strat="abc"}',
    'f{x="abc"}',
    '"abc"',
    'm{asc="b"}',
    # case values
    "r{poli=S}",
    "r{poli=s}",
    "r{poli=Z}",
    "r{map=t}",
    "r{map=f}",
    "r{map=y}",
    "r{map=n}",
    "r{map=1}",
    "r{map=0}",
    # whitespace torture (no newlines here; those are built into differ)
    " m | r ",
    "\tm\t|\tr\t",
    "m {asc = b}",
    "/ vert < 1000 ? m ; ",
    "r { sep = g f }",
    "f{ move = - 80 }",
]

# "@" is the insertion point; it never occurs in pool strings.
WRAPPERS = [
    "(@)",
    "@|m",
    "m|@",
    "/vert<1000?@;",
    "/vert<1000?m:@;",
    "/edge>3?(@):m;",
    "r{sep=@}",
    "m{asc=@,low=@}",
    "n{sep=@,ole=s,ose=g}",
    "@@",
]

ALPHABET = 'mrfgbdhcsnxzoevutSTFN0123456789{}=,;/?:()!<>+-*%|&. \t"eE'


def mutate(rng, s):
    op = rng.randrange(6)
    if op == 0 and s:  # delete a char
        i = rng.randrange(len(s))
        return s[:i] + s[i + 1 :]
    if op == 1:  # insert a char
        i = rng.randrange(len(s) + 1)
        return s[:i] + rng.choice(ALPHABET) + s[i:]
    if op == 2 and s:  # replace a char
        i = rng.randrange(len(s))
        return s[:i] + rng.choice(ALPHABET) + s[i + 1 :]
    if op == 3 and len(s) > 1:  # duplicate a slice
        i = rng.randrange(len(s))
        j = min(len(s), i + rng.randrange(1, 8))
        return s[:j] + s[i:j] + s[j:]
    if op == 4 and s:  # case-flip a char
        i = rng.randrange(len(s))
        return s[:i] + s[i].swapcase() + s[i + 1 :]
    if op == 5 and s:  # transpose two adjacent chars
        i = rng.randrange(len(s) - 1) if len(s) > 1 else 0
        return s[:i] + s[i + 1 : i + 2] + s[i : i + 1] + s[i + 2 :]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=20000, help="number of random mutations to emit")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--seeds", action="append", default=[], help="file(s) of seed strings, one per line (e.g. ./dump output)"
    )
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pool = list(CORPUS)
    for path in args.seeds:
        with open(path) as fh:
            pool.extend(line.rstrip("\n") for line in fh if line.strip())

    out = sys.stdout
    for s in pool:  # the pool itself, verbatim
        out.write(s + "\n")

    for _ in range(args.count):
        kind = rng.randrange(10)
        if kind < 5:  # mutate a pool string 1-4 times
            s = rng.choice(pool)
            for _ in range(rng.randrange(1, 5)):
                s = mutate(rng, s)
        elif kind < 7:  # splice two pool strings
            a, b = rng.choice(pool), rng.choice(pool)
            i = rng.randrange(len(a) + 1)
            j = rng.randrange(len(b) + 1)
            s = a[:i] + b[j:]
        elif kind < 9:  # wrap a pool string in a structure
            s = WRAPPERS[rng.randrange(len(WRAPPERS))].replace("@", rng.choice(pool))
        else:  # pure noise
            s = "".join(rng.choice(ALPHABET) for _ in range(rng.randrange(1, 40)))
        s = s.replace("\n", " ")  # line protocol: no embedded newlines
        out.write(s + "\n")


if __name__ == "__main__":
    main()
