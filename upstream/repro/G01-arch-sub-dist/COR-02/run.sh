#!/bin/sh
# Usage: run.sh <libdir>   (pristine: $INFRA/asan/lib ; patched: $WORK/build/lib)
export LD_LIBRARY_PATH=$1 UBSAN_OPTIONS=print_stacktrace=1 ASAN_OPTIONS=detect_leaks=1
D=$(dirname "$0"); C=$D/../common; T=$D/../tgt
for f in cmplt_bad; do r=$($C/archload $T/$f.tgt 2>&1); echo "$f: ret=$(echo "$r" | sed -n 's/^load ret=//p') sanitizer-hits=$(echo "$r" | grep -c 'Sanitizer\|runtime error')"; done
