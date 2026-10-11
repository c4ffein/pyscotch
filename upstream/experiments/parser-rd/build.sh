#!/bin/sh -e
# Build the differential harness (differ) and the seed dumper (dump)
# against the prepared Scotch source copy's headers and the stock
# (unsuffixed) libscotch.so produced by `make build-gpart`.
#
# The compile flags MUST match the ones the stock library was built with
# (patches/Makefile.inc.default) wherever they affect header-visible types:
# no INTSIZE define (default INT) and -DSCOTCH_RENAME (internal symbols are
# _SCOTCH-prefixed, which is how we reach stratParserParse and the strategy
# tables directly).

cd "$(dirname "$0")"
ROOT=../../..
SRC=$ROOT/build/scotch-src/src/libscotch
INC=$ROOT/build/scotch-src/include
LIBDIR=$(cd "$ROOT/scotch-builds/bin" && pwd)

test -f "$SRC/parser.h" || { echo "run 'make build-gpart' at the repo root first (prepares $SRC and $LIBDIR)"; exit 1; }

CFLAGS="-O2 -g -Wall -Wextra -Wno-unused-parameter -U_FORTIFY_SOURCE \
  -DCOMMON_FILE_COMPRESS_GZ -DCOMMON_PTHREAD -DCOMMON_PTHREAD_AFFINITY_LINUX \
  -DCOMMON_RANDOM_FIXED_SEED -DSCOTCH_PTHREAD -DSCOTCH_RENAME"

gcc $CFLAGS -I"$SRC" parser_rd.c differ.c -o differ \
  "$LIBDIR/libscotch.so" -lz -lm -lpthread -Wl,-rpath,"$LIBDIR"

gcc -O2 -g -Wall -I"$INC" dump.c -o dump \
  "$LIBDIR/libscotch.so" "$LIBDIR/libscotcherr.so" -lz -lm -lpthread -Wl,-rpath,"$LIBDIR"

echo "built: differ, dump"
