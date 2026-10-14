#!/bin/bash
# build.sh BUILDDIR -> compiles g21fi against $BUILDDIR into ./bin_<name>/g21fi
B=$1; name=$(basename $B); here=$(cd $(dirname $0) && pwd)
CF="$(grep '^CFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
LF="$(grep '^LDFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
mkdir -p $here/bin_$name
mpicc $CF -DSCOTCH_PTSCOTCH -I$B/include -I$B/src/libscotch $here/g21fi.c -o $here/bin_$name/g21fi -L$B/lib -lptscotch -lscotch -lptscotcherr $LF -ldl || exit 1
echo built $here/bin_$name/g21fi
