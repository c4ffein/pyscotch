#!/bin/bash
# scan.sh LIBDIR BIN NP FAILRANK NTH_FROM NTH_TO -- args...   (one line per nth; HANG = 15 s timeout)
LIB=$1; BIN=$2; NP=$3; FR=$4; FROM=$5; TO=$6; shift 6; [ "$1" = "--" ] && shift
here=$(dirname $0)
export LD_LIBRARY_PATH=$LIB UBSAN_OPTIONS=print_stacktrace=1
export ASAN_OPTIONS=detect_leaks=0:verify_asan_link_order=0:abort_on_error=0
for n in $(seq $FROM $TO); do
  out=$(timeout 15 mpirun --oversubscribe -np $NP -x LD_PRELOAD=$here/fishim.so -x FI_RANK=$FR -x FI_NTH=$n -x ASAN_OPTIONS -x UBSAN_OPTIONS -x LD_LIBRARY_PATH $BIN "$@" 2>&1); rc=$?
  s=$(echo "$out" | grep -E "fishim:|ERROR|rc=|runtime error|SUMMARY" | sed -E 's/==[0-9]+==//' | cut -c1-150 | sort | uniq -c | sed -E 's/^ +//' | tr '\n' ';')
  [ $rc -eq 124 ] && s="HANG; $s"
  echo "nth=$n exit=$rc :: $s"
done
