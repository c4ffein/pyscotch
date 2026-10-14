#!/bin/sh
# Usage: run.sh <libdir>   (pristine: $INFRA/asan/lib ; patched: $WORK/build/lib)
export LD_LIBRARY_PATH=$1 UBSAN_OPTIONS=print_stacktrace=1 ASAN_OPTIONS=detect_leaks=1
D=$(dirname "$0"); C=$D/../common; T=$D/../tgt
for f in dist_ok dist_bad dist_var dist_sub dist_zero dist_subsub; do r=$($C/archtrip $T/$f.tgt $D/out_$f.tgt 2>&1); echo "$f: $(echo "$r" | grep -E 'ret=' | tr '\n' ' ') sanitizer-hits=$(echo "$r" | grep -c 'Sanitizer\|runtime error')"; done
