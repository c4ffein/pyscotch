#!/bin/sh
# mkinject.sh <bgraph_bipart_df.c> <out.so> <build tree>
# Builds a shared object that interposes _SCOTCHbgraphBipartDf() (LD_PRELOAD before libscotch.so)
# from the given source, with a test-only NaN injection controlled by environment variables:
# INJ_CALL (n-th call of bgraphBipartDf), INJ_THRD (thread), INJ_PASS (pass counter value),
# INJ_VERT (offset of the vertex in the thread's range, or negative: offset from the range end).
SRC=$1; OUT=$2; BLD=$3; TMP=$(mktemp -d); cp "$SRC" $TMP/df.c
python3 -I - "$TMP/df.c" <<'PY'
import sys
p = sys.argv[1]; s = open (p).read ()
s = s.replace ('#include "bgraph_bipart_df.h"\n', '#include "bgraph_bipart_df.h"\n#include <stdlib.h>\nstatic long injthrd = -1, injpass = -1, injvert = -1, injcall = -1, callnum = 0; /* TEST INJECTION */\n', 1)
s = s.replace ('  difotax = loopptr->difotax;\n', '  { const char * e; e = getenv ("INJ_THRD"); injthrd = e ? atol (e) : -1; e = getenv ("INJ_PASS"); injpass = e ? atol (e) : -1; e = getenv ("INJ_VERT"); injvert = e ? atol (e) : -1; e = getenv ("INJ_CALL"); injcall = e ? atol (e) : -1; } /* TEST INJECTION */\n  difotax = loopptr->difotax;\n', 1)
s = s.replace ('        if (isnan (diffval)) {', '        if ((injcall == callnum) && (injthrd == thrdnum) && (injpass == passnum) && ((injvert == vertnum - vertbas) || ((injvert < 0) && (vertnum == vertnnd + injvert)))) { fprintf (stderr, "INJECT NaN thrd=%d pass=%ld vertnum=%ld vertbas=%ld vancnnd=%ld vertnnd=%ld vancnnt=%ld\\n", thrdnum, (long) passnum, (long) vertnum, (long) vertbas, (long) vancnnd, (long) vertnnd, (long) vancnnt); diffval = NAN; } /* TEST INJECTION */\n        if (isnan (diffval)) {', 1)
s = s.replace ('  loopdat.abrtval = 0;                            /* Nobody wants to abort yet */\n', '  loopdat.abrtval = 0;                            /* Nobody wants to abort yet */\n  callnum ++; if (getenv ("INJ_CALL") != NULL) fprintf (stderr, "DFCALL %ld: vertnbr=%ld veex=%d thrdnbr=%d passnbr=%ld\\n", callnum, (long) grafptr->s.vertnbr, grafptr->veextax != NULL, thrdnbr, (long) paraptr->passnbr); /* TEST INJECTION */\n', 1)
assert s.count ('TEST INJECTION') == 4, s.count ('TEST INJECTION')
open (p, 'w').write (s)
PY
CF="$(grep '^CFLAGS' $BLD/src/Makefile.inc | cut -d= -f2-)"
gcc $CF -I$BLD/src/libscotch -I$BLD/include -shared -fPIC -o "$OUT" $TMP/df.c && echo "built $OUT"
rm -rf $TMP
