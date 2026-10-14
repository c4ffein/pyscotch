#!/bin/sh
# Usage: run.sh <libdir>   (pristine: $INFRA/asan/lib ; patched: $WORK/build/lib)
export LD_LIBRARY_PATH=$1 UBSAN_OPTIONS=print_stacktrace=1 ASAN_OPTIONS=detect_leaks=1
D=$(dirname "$0"); C=$D/../common; T=$D/../tgt
for f in sub_one sub_one_hcub sub_one0; do r=$($C/archtrip $T/$f.tgt $D/out_$f.tgt 2>&1); echo "$f: $(echo "$r" | grep -E 'ret=' | tr '\n' ' ') sanitizer-hits=$(echo "$r" | grep -c 'Sanitizer\|runtime error')"; done
for v in 5 0; do r=$($D/build2one /tmp/claude-1000/-home-dev-workspace-pyscotch/087f3d41-a5d8-4b0a-9260-769d70cf8179/scratchpad/infra/v7.0.17/src/check/data/m4x4.grf $v 2>&1); echo "SCOTCH_archBuild2 m4x4 vertex $v: ret=$(echo "$r" | sed -n 's/^build2 ret=//p') sanitizer-hits=$(echo "$r" | grep -c 'Sanitizer\|runtime error')"; done
