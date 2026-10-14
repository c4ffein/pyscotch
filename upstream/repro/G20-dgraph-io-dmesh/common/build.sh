#!/bin/bash
# build.sh BUILDDIR : compile dgload and dmload against BUILDDIR into bin_<basename BUILDDIR>/
B=$1; name=$(basename $B); here=$(cd $(dirname $0) && pwd)
CF="$(grep '^CFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
LF="$(grep '^LDFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
mkdir -p $here/bin_$name
for p in dgload dmload; do
  mpicc $CF -DSCOTCH_PTSCOTCH -I$B/include -I$B/src/libscotch $here/$p.c -o $here/bin_$name/$p -L$B/lib -lptscotch -lscotch -lptscotcherr $LF -ldl || exit 1
done
echo built in $here/bin_$name
