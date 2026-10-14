#!/bin/sh
# Usage: run.sh <libdir>   (pristine: $INFRA/asan/lib ; patched: $WORK/build/lib)
export LD_LIBRARY_PATH=$1 UBSAN_OPTIONS=print_stacktrace=1 ASAN_OPTIONS=detect_leaks=1
D=$(dirname "$0"); C=$D/../common; T=$D/../tgt
# mate links against internal symbols of a SCOTCH_RENAME build; prints pass number and single vertex per level
for n in 5 9 11; do echo "n=$n:"; $D/mate $n | sed 's/^/  /'; done
fails=0; for n in $(seq 2 64) 100 1023; do $D/mate $n > /dev/null 2>&1 || fails=$((fails+1)); done; echo "coverage sweep failures (n=2..64,100,1023): $fails"
