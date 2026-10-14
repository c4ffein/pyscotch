#!/bin/sh
# Usage: run.sh <libdir>   (pristine: $INFRA/asan/lib ; patched: $WORK/build/lib)
export LD_LIBRARY_PATH=$1 UBSAN_OPTIONS=print_stacktrace=1 ASAN_OPTIONS=detect_leaks=1
D=$(dirname "$0"); C=$D/../common; T=$D/../tgt
r=$($C/subapi 0 0 2>&1); echo "SCOTCH_archSub {0,0} (Build fails): ret=$(echo "$r" | sed -n 's/^archSub ret=//p') leak-reports=$(echo "$r" | grep -c 'LeakSanitizer') other-sanitizer-hits=$(echo "$r" | grep -c 'AddressSanitizer: [^l]\|runtime error')"
