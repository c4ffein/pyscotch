#!/bin/sh
# usage: run.sh <build-tree> <outdir> [runs]
# 30 fresh-process runs of gord (bump.grf) and mord (cube_8.msh) at 1, 2 and 4
# threads with SCOTCH_DETERMINISTIC=1; counts the runs whose output differs
# from the first 1-thread run.
T=$1; O=$2; N=${3:-30}; D=$T/src/check/data
mkdir -p $O
export LD_LIBRARY_PATH=$T/lib ASAN_OPTIONS=detect_leaks=0 SCOTCH_DETERMINISTIC=1
for prog in gord mord; do
  if [ $prog = gord ]; then in=$D/bump.grf; else in=$D/cube_8.msh; fi
  SCOTCH_PTHREAD_NUMBER=1 $T/bin/$prog $in $O/$prog.ref 2>/dev/null
  for t in 1 2 4; do
    diff=0
    i=0
    while [ $i -lt $N ]; do
      SCOTCH_PTHREAD_NUMBER=$t $T/bin/$prog $in $O/$prog.cur 2>/dev/null
      if ! cmp -s $O/$prog.ref $O/$prog.cur; then diff=$((diff+1)); cp $O/$prog.cur $O/$prog.diff.$t; fi
      i=$((i+1))
    done
    echo "$prog threads=$t runs=$N differing_from_1thread_ref=$diff"
  done
done
