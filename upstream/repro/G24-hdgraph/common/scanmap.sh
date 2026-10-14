#!/bin/bash
WORK=/tmp/claude-1000/-home-dev-workspace-pyscotch/087f3d41-a5d8-4b0a-9260-769d70cf8179/scratchpad/work/G24-hdgraph; C=$WORK/repro/common; D=$WORK/scotch/src/check/data
R0="$(seq 295 322) $(seq 444 457) 582 586"; R1="$(seq 307 334) $(seq 458 468)"; R2="$(seq 294 311) 434 438"
for b in basefi buildfi; do
  ( $C/scan2.sh $WORK/$b/lib $C/bin_$b/mapfi 3 0 "$R0" -- $D/m16x16.grf cmplt:5 > $C/scans/map_${b}_np3_r0.txt 2>&1 ) &
  ( $C/scan2.sh $WORK/$b/lib $C/bin_$b/mapfi 3 1 "$R1" -- $D/m16x16.grf cmplt:5 > $C/scans/map_${b}_np3_r1.txt 2>&1 ) &
  ( $C/scan2.sh $WORK/$b/lib $C/bin_$b/mapfi 3 2 "$R2" -- $D/m16x16.grf cmplt:5 > $C/scans/map_${b}_np3_r2.txt 2>&1 ) &
  wait
done
echo done > $C/scans/map.done
