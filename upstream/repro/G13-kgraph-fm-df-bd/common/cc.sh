#!/bin/sh
# usage: cc.sh <build-tree> <out> <sources...>  -- compiles a harness against an ASan build tree
B=$1; shift; out=$1; shift
CF="$(grep '^CFLAGS' $B/src/Makefile.inc | cut -d= -f2-)"
exec gcc $CF -DSCOTCH_VERSION_NUM=7 -DSCOTCH_RELEASE_NUM=0 -DSCOTCH_PATCHLEVEL_NUM=17 \
  -I$B/src/libscotch -I$B/include -I$(dirname $0) "$@" -o $out -L$B/lib -lscotch -lscotcherr -lz -lm -lpthread
