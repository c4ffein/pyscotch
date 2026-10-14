#!/bin/bash
# scan2.sh LIBDIR BIN NP FAILRANK "NTH LIST" -- args...  (fishim2: live-block accounting; HANG = 15 s timeout)
LIB=$1; BIN=$2; NP=$3; FR=$4; LIST=$5; shift 5; [ "$1" = "--" ] && shift
here=$(cd $(dirname $0) && pwd)
export LD_LIBRARY_PATH=$LIB UBSAN_OPTIONS=print_stacktrace=1
for n in $LIST; do
  out=$(timeout 15 mpirun --oversubscribe -np $NP -x LD_PRELOAD=$here/fishim2.so -x FI_RANK=$FR -x FI_NTH=$n -x UBSAN_OPTIONS -x LD_LIBRARY_PATH $BIN "$@" 2>&1); rc=$?
  s=$(echo "$out" | grep -E "fishim: rank [0-9]+: (failing|live)|ERROR|rc=|runtime error|signal [0-9]" | sed -E 's/==[0-9]+==//' | cut -c1-120 | sort | uniq -c | sed -E 's/^ +//' | tr '\n' ';')
  [ $rc -eq 124 ] && s="HANG; $s"
  echo "nth=$n exit=$rc :: $s"
done
