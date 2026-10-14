#!/bin/sh
# usage: dump_usage.sh <build tree> <output dir>   -- writes the -h text of every tool of <build tree>/bin
B=$1; U=$2; mkdir -p "$U"
export LD_LIBRARY_PATH=$B/lib ASAN_OPTIONS=detect_leaks=0
for b in $(ls "$B/bin"); do
  case $b in
    dg*) mpirun --oversubscribe -np 1 "$B/bin/$b" -h > "$U/$b.txt" 2>&1 ;;
    *)   "$B/bin/$b" -h > "$U/$b.txt" 2>&1 ;;
  esac
done
