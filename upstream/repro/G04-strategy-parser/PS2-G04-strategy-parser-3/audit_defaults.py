import re, sys, glob
# For every *_st.c: map method default struct name -> number of &stratdummy in its initializer,
# and method -> number of STRATPARAMSTRAT parameters whose dbasptr points into that default.
for f in sorted(glob.glob(sys.argv[1] + '/src/libscotch/*_st.c')):
    src = open(f).read()
    defs = {}
    for m in re.finditer(r'\}\s*(\w+default\w*)\s*=\s*(\{.*?\}\s*\});', src, re.S):
        defs[m.group(1)] = m.group(2).count('&stratdummy')
    need = {}
    for m in re.finditer(r'\{\s*\w+,\s*STRATPARAMSTRAT,\s*"(\w+)",\s*\(byte \*\)\s*&(\w+)\.param', src):
        need.setdefault(m.group(2), []).append(m.group(1))
    for d, names in need.items():
        have = defs.get(d, None)
        flag = '' if have == len(names) else '   <== MISMATCH'
        print(f"{f.split('/')[-1]:28s} {d:32s} strat params {names} dummies={have}{flag}")
