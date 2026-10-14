#!/bin/sh
# usage: build.sh <build tree>   (compiles all G25 reproducers against that tree's libraries)
B=$1; R=$(dirname $0)
CF="-g -fsanitize=address,undefined -I$B/include -I$B/src/libscotchmetis"
L="-L$B/lib -lscotch -lscotcherr -lz -lm -lpthread"
set -e
gcc $CF -DSCOTCH_METIS_VERSION=5 $R/CLI-02/cli02.c -o $R/CLI-02/cli02 -lscotchmetisv5 $L
gcc $CF -DSCOTCH_METIS_VERSION=5 $R/CLI-03/cli03.c -o $R/CLI-03/cli03 -lscotchmetisv5 $L
gcc $CF -DSCOTCH_METIS_VERSION=5 $R/CLI-06/cli06.c -o $R/CLI-06/cli06 -lscotchmetisv5 $L
gcc $CF -DSCOTCH_METIS_VERSION=5 $R/CLI-07/cli07.c -o $R/CLI-07/cli07 -lscotchmetisv5 $L
mpicc $CF -DSCOTCH_METIS_VERSION=3 -DSCOTCH_PTSCOTCH $R/CLI-07/pcli07.c -o $R/CLI-07/pcli07 -lptscotchparmetisv3 -lptscotch -lptscotcherr $L
gcc $CF -DSCOTCH_METIS_VERSION=5 $R/CLI-08/cli08.c -o $R/CLI-08/cli08 -lscotchmetisv5 $L
gcc $CF -DSCOTCH_METIS_VERSION=5 $R/CLI-19/cli19.c -o $R/CLI-19/cli19 -lscotchmetisv5 $L
echo built
