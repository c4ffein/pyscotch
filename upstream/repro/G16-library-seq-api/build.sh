#!/bin/sh
# Usage: build.sh <build tree> <output suffix>
# Compiles every reproducer against the libraries of the given build tree
# (an ASan+UBSan build; the reproducers are compiled with the same sanitizers).
set -e
B=$1
S=$2
R=$(dirname "$0")
CF="-O0 -g -fsanitize=address,undefined -fno-omit-frame-pointer -I$B/include -L$B/lib -Wl,-rpath,$B/lib"
if grep -q INTSIZE64 "$B/src/Makefile.inc"; then CF="$CF -DINTSIZE64 -DIDXSIZE64"; fi
gcc   $CF "$R/API-14/diam.c"    -o "$R/API-14/diam$S"    -lscotch -lscotcherr -lz -lm -lpthread
gcc   $CF "$R/API-16/remap.c"   -o "$R/API-16/remap$S"   -lscotch -lscotcherr -lz -lm -lpthread
gcc   $CF "$R/API-19/stat.c"    -o "$R/API-19/stat$S"    -lscotch -lscotcherr -lz -lm -lpthread
mpicc $CF "$R/API-19/dstat.c"   -o "$R/API-19/dstat$S"   -lptscotch -lscotch -lptscotcherr -lz -lm -lpthread
gcc   $CF "$R/API-21/tabload.c" -o "$R/API-21/tabload$S" -lscotch -lscotcherr -lz -lm -lpthread
mpicc $CF "$R/API-18/dview.c"   -o "$R/API-18/dview$S"   -lptscotch -lscotch -lptscotcherr -lz -lm -lpthread
echo "built with $B -> suffix '$S'"
