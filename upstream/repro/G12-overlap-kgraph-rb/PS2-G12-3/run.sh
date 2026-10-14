#!/bin/sh
# usage: run.sh <lib-dir> <bin-dir> <check-dir-with-data> ; compares gpart results for 1, 2, 4 threads with SCOTCH_DETERMINISTIC=1
L=$1; B=$2; C=$3; D=$(mktemp -d); cd $C || exit 1
export ASAN_OPTIONS=detect_leaks=0 SCOTCH_DETERMINISTIC=1 LD_LIBRARY_PATH=$L
for t in 1 2 4; do
  SCOTCH_PTHREAD_NUMBER=$t $B/gpart -o 9 data/bump.grf $D/ovl_t$t.map -Mr{sep=f} > /dev/null 2>&1
  SCOTCH_PTHREAD_NUMBER=$t $B/gpart 9 data/bump.grf $D/rb_t$t.map -Cr > /dev/null 2>&1
done
for k in ovl rb; do echo "$k: t1-vs-t2=$(diff $D/${k}_t1.map $D/${k}_t2.map | grep -c '^[<>]') t2-vs-t4=$(diff $D/${k}_t2.map $D/${k}_t4.map | grep -c '^[<>]')"; done
rm -rf $D
