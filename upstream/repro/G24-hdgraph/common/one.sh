#!/bin/bash
# one.sh LIBDIR BIN NP FAILRANK NTH MODE [graph] [strategy] : one injected run with fishim2 (live-block accounting); compact summary
WORK=/tmp/claude-1000/-home-dev-workspace-pyscotch/087f3d41-a5d8-4b0a-9260-769d70cf8179/scratchpad/work/G24-hdgraph
here=$(cd $(dirname $0) && pwd); LIB=$1; BIN=$2; NP=$3; FR=$4; NTH=$5; MODE=$6; G=${7:-$WORK/scotch/src/check/data/m16x16.grf}; STRAT=${8:-}
export LD_LIBRARY_PATH=$LIB UBSAN_OPTIONS=print_stacktrace=1
out=$(timeout 20 mpirun --oversubscribe -np $NP -x LD_PRELOAD=$here/fishim2.so -x FI_RANK=$FR -x FI_NTH=$NTH -x UBSAN_OPTIONS -x LD_LIBRARY_PATH $BIN $G "$STRAT" $MODE 2>&1); rc=$?
s=$(echo "$out" | grep -E "fishim: rank [0-9]+: (failing|live)|ERROR|rc=|runtime error|signal" | grep -v "backtrace" | sed -E 's/==[0-9]+==//' | sort | uniq -c | sed -E 's/^ +//' | cut -c1-110 | tr '\n' ';')
[ $rc -eq 124 ] && s="HANG; $s"
echo "[$(basename $(dirname $LIB)) np=$NP r=$FR nth=$NTH $MODE strat=$STRAT] exit=$rc :: $s"
