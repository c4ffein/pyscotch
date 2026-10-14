#!/bin/bash
# scanall.sh LIBDIR BINDIR TAG NP MAXNTH : full per-rank scans in parallel, mode user
WORK=/tmp/claude-1000/-home-dev-workspace-pyscotch/087f3d41-a5d8-4b0a-9260-769d70cf8179/scratchpad/work/G24-hdgraph
C=$WORK/repro/common; D=$WORK/scotch/src/check/data
LIB=$1; BIN=$2; TAG=$3; NP=$4; MAX=$5
for r in $(seq 0 $((NP-1))); do
  ( $C/scan.sh $LIB $BIN/orderfi $NP $r 0 $MAX -- $D/m16x16.grf "" user > $C/scans/${TAG}_np${NP}_r${r}.txt 2>&1 ) &
done
wait
echo done > $C/scans/${TAG}_np${NP}.done
