#!/bin/sh
## Compare the object lists of the Makefiles with the source lists of
## the CMake files, for each library of the Scotch tree. Exits with a
## non-zero status if some C source file is built by only one of the
## two build systems.
## Usage: ci/check_sources.sh [path to src directory]

srcdir="${1:-src}"
status=0

# makeobjs <makefile> <variable>: C sources of a Makefile object list
makeobjs() {
  sed -n "/^$2[ 	]*=/,/[^\\\\]\$/p" "$1" | \
  sed -n 's/^.*[ 	=]\([a-z0-9_]*\)\$(OBJ).*$/\1.c/p' | sort -u
}

# cmakesrcs <CMakeLists.txt> <variable>: C sources of a CMake source list
cmakesrcs() {
  sed -n "/^[ 	]*set($2\$/,/)/p" "$1" | \
  sed -n 's/^[ 	]*\([^ 	#]*\/\)*\([a-z0-9_]*\.c\)[ 	)]*$/\2/p' | sort -u
}

# compare <name> <makefile> <variable> <cmakefile> <variable>
compare() {
  tmpdir="${TMPDIR:-/tmp}"
  makeobjs "$2" "$3" > "$tmpdir/check_sources_$$.make"
  cmakesrcs "$4" "$5" > "$tmpdir/check_sources_$$.cmake"
  diff "$tmpdir/check_sources_$$.make" "$tmpdir/check_sources_$$.cmake" > "$tmpdir/check_sources_$$.diff"
  if [ -s "$tmpdir/check_sources_$$.diff" ] ; then
    echo "$1: source lists differ ('<': Makefile only, '>': CMake only)"
    grep '^[<>]' "$tmpdir/check_sources_$$.diff"
    status=1
  fi
  rm -f "$tmpdir/check_sources_$$.make" "$tmpdir/check_sources_$$.cmake" "$tmpdir/check_sources_$$.diff"
}

compare libscotch   "$srcdir/libscotch/Makefile" LIBSCOTCHDEPS   "$srcdir/libscotch/CMakeLists.txt" SCOTCH_C_SOURCES
compare libptscotch "$srcdir/libscotch/Makefile" LIBPTSCOTCHDEPS "$srcdir/libscotch/CMakeLists.txt" PTSCOTCH_C_SOURCES
compare libesmumps  "$srcdir/esmumps/Makefile"   LIBESMUMPSDEPS  "$srcdir/esmumps/CMakeLists.txt"   esmumps_src

exit $status
