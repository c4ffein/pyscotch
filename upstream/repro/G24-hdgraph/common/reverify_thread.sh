#!/bin/bash
# Re-verification of the key readings with the MPI_Init_thread(MPI_THREAD_MULTIPLE) drivers and per-routine injection (FI_FUNC)
WORK=/tmp/claude-1000/-home-dev-workspace-pyscotch/087f3d41-a5d8-4b0a-9260-769d70cf8179/scratchpad/work/G24-hdgraph; C=$WORK/repro/common; D=$WORK/scotch/src/check/data
cd $C
for f in "0 hdgraphOrderSi2 0" "0 dorderNew 1" "0 hdgraphInduceList 3" "0 hdgraphInduceList 4" "0 hdgraphGather 1" "0 dorderNewSequ 0" "2 dorderNewSequ 0" "1 hdgraphGather 1" "0 vdgraphGatherAll 0" "0 stratParserParse 0"; do
  set -- $f
  for b in basefi buildfi; do ./onef.sh $WORK/$b/lib $C/bin_$b/orderfi 3 $1 $2 $3 $D/m16x16.grf "" rc; done
done
for f in "0 dgraphInduce2 4" "2 dgraphInduce2 5" "0 kgraphInit 0" "0 kdgraphMapRbAdd2 0"; do
  set -- $f
  for b in basefi buildfi; do ./onef.sh $WORK/$b/lib $C/bin_$b/mapfi 3 $1 $2 $3 $D/m16x16.grf cmplt:5; done
done
echo "=== no injection, 5 runs each, both drivers (threaded folds)"
for b in basefi buildfi; do for i in 1 2 3 4 5; do ./onef.sh $WORK/$b/lib $C/bin_$b/orderfi 3 0 none -1 $D/m16x16.grf "" check; done; done
