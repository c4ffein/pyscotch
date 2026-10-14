#!/bin/sh
# cc.sh <build tree> <source.c> <output> [extra flags] : compile a driver against a build tree (ASan+UBSan like the tree)
B=$1; S=$2; O=$3; shift 3
CF="$(grep '^CFLAGS' $B/src/Makefile.inc | cut -d= -f2- | sed 's/-DSCOTCH_RENAME//')"
gcc $CF -I$B/include -I$B/src/libscotch "$S" -o "$O" -L$B/lib -lscotch -lscotcherr -lm -lz -lpthread "$@"
