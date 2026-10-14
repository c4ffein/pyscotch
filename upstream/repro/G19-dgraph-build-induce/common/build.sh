#!/bin/bash
# build.sh BUILDDIR : compile every reproducer against BUILDDIR (lib + internal headers) into repro/<ID>/bin_<name>/
B=$1; name=$(basename $B); here=$(cd $(dirname $0)/..; pwd)
CF="$(grep '^CFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"; LF="$(grep '^LDFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
for src in DGR-05/buildfi DGR-06/inducefi PS-DGR-3/inducefi DGR-08/ghstfi DGR-18/grid3dfi DGR-11/chk DGR-12/lab DGR-21/mchk; do
  d=$(dirname $src); p=$(basename $src); mkdir -p $here/$d/bin_$name
  mpicc $CF -DSCOTCH_PTSCOTCH -I$B/include -I$B/src/libscotch $here/$src.c -o $here/$d/bin_$name/$p -L$B/lib -lptscotch -lscotch -lptscotcherr $LF -ldl || exit 1
done
echo built against $B
