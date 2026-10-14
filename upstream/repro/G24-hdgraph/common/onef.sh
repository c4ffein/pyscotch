#!/bin/bash
# onef.sh LIBDIR BIN NP FAILRANK FUNC NTH args... : fail the NTH allocation made by routine FUNC on FAILRANK (fishim2, FI_FUNC)
here=$(cd $(dirname $0) && pwd); LIB=$1; BIN=$2; NP=$3; FR=$4; FUNC=$5; NTH=$6; shift 6
export LD_LIBRARY_PATH=$LIB UBSAN_OPTIONS=print_stacktrace=1
out=$(timeout 20 mpirun --oversubscribe -np $NP -x LD_PRELOAD=$here/fishim2.so -x FI_RANK=$FR -x FI_FUNC=$FUNC -x FI_NTH=$NTH -x UBSAN_OPTIONS -x LD_LIBRARY_PATH $BIN "$@" 2>&1); rc=$?
s=$(echo "$out" | grep -E "fishim: rank [0-9]+: (failing|live)|ERROR|rc=|runtime error|signal" | grep -v backtrace | sed -E 's/==[0-9]+==//; s/ \(max [0-9]+\)//' | sort | uniq -c | sed -E 's/^ +//' | cut -c1-110 | tr '\n' ';')
[ $rc -eq 124 ] && s="HANG; $s"
echo "[$(basename $(dirname $LIB)) np=$NP r=$FR $FUNC#$NTH] exit=$rc :: $s"
