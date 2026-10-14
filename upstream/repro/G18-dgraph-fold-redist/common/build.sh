#!/bin/bash
# build.sh BUILDDIR  -> compiles the drivers against $BUILDDIR/lib and headers, into ./bin_<name>
B=$1; name=$(basename $B); here=$(dirname $0)
CF="$(grep '^CFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
LF="$(grep '^LDFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
mkdir -p $here/bin_$name
for p in foldfi gatherfi; do
  mpicc $CF -DSCOTCH_PTSCOTCH -I$B/include -I$B/src/libscotch $here/$p.c -o $here/bin_$name/$p -L$B/lib -lptscotch -lscotch -lptscotcherr $LF -ldl || exit 1
done
echo built in $here/bin_$name
