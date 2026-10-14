#!/bin/sh
# Build a scratch copy of a src/check test program with one deliberate
# corruption inserted, run it, and report its exit status.
#
# usage: mutate.sh <build tree> <test.c> <anchor regexp> <C line to insert before the first anchor match> <args...>
# The scratch copy is compiled with the build tree's CFLAGS against its lib/.
set -u
BUILD=$1; SRC=$2; ANCHOR=$3; LINE=$4; shift 4
SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/mutate.XXXXXX")
NAME=$(basename "$SRC" .c)
python3 -I - "$SRC" "$ANCHOR" "$LINE" "$SCRATCH/$NAME.c" <<'EOF'
import re, sys
src, anchor, line, dst = sys.argv[1:]
out = []
done = False
for l in open(src):
    if not done and re.search(anchor, l):
        indent = re.match(r"^\s*", l).group(0)
        out.append(indent + line + "\n")
        done = True
    out.append(l)
if not done:
    sys.exit("anchor not found: " + anchor)
open(dst, "w").write("".join(out))
EOF
[ $? -eq 0 ] || exit 99
CF=$(grep '^CFLAGS' "$BUILD/src/Makefile.inc" | cut -d= -f2-)
LF=$(grep '^LDFLAGS' "$BUILD/src/Makefile.inc" | cut -d= -f2-)
gcc $CF -I"$BUILD/include" -I"$BUILD/src/check" -L"$BUILD/lib" "$SCRATCH/$NAME.c" -o "$SCRATCH/$NAME" -lscotch -lscotcherr $LF || exit 98
LD_LIBRARY_PATH="$BUILD/lib" "$SCRATCH/$NAME" "$@" > "$SCRATCH/out.txt" 2>&1
RC=$?
grep -v '^Strat\|^$' "$SCRATCH/out.txt" | head -${MUTATE_LINES:-4}
echo "rc=$RC"
rm -rf "$SCRATCH"
exit $RC
