#!/bin/sh
# mktrace.sh <bgraph_bipart_df.c> <out.so> <build tree> : like mkinject.sh, plus a trace of every
# barrier / reduction / scan / return per thread (stderr), and "DF END" when bgraphBipartDf() returns.
SRC=$1; OUT=$2; BLD=$3; TMP=$(mktemp -d); cp "$SRC" $TMP/df.c
python3 -I - "$TMP/df.c" <<'PY'
import sys, re
p = sys.argv[1]; s = open (p).read ()
s = s.replace ('#include "bgraph_bipart_df.h"\n', '#include "bgraph_bipart_df.h"\n#include <stdlib.h>\nstatic long injthrd = -1, injpass = -1, injvert = -1, injcall = -1, callnum = 0; /* TEST INJECTION */\n#define TRACE(s) fprintf (stderr, "T%d " s " line %d\\n", thrdnum, __LINE__)\n', 1)
s = s.replace ('  difotax = loopptr->difotax;\n', '  { const char * e; e = getenv ("INJ_THRD"); injthrd = e ? atol (e) : -1; e = getenv ("INJ_PASS"); injpass = e ? atol (e) : -1; e = getenv ("INJ_VERT"); injvert = e ? atol (e) : -1; e = getenv ("INJ_CALL"); injcall = e ? atol (e) : -1; } /* TEST INJECTION */\n  difotax = loopptr->difotax;\n', 1)
s = s.replace ('        if (isnan (diffval)) {', '        if ((injcall == callnum) && (injthrd == thrdnum) && (injpass == passnum) && ((injvert == vertnum - vertbas) || ((injvert < 0) && (vertnum == vertnnd + injvert)))) { fprintf (stderr, "INJECT NaN thrd=%d pass=%ld vertnum=%ld vertbas=%ld vancnnd=%ld vertnnd=%ld vancnnt=%ld\\n", thrdnum, (long) passnum, (long) vertnum, (long) vertbas, (long) vancnnd, (long) vertnnd, (long) vancnnt); diffval = NAN; } /* TEST INJECTION */\n        if (isnan (diffval)) {', 1)
s = s.replace ('  loopdat.abrtval = 0;                            /* Nobody wants to abort yet */\n', '  loopdat.abrtval = 0;                            /* Nobody wants to abort yet */\n  callnum ++; if (getenv ("INJ_CALL") != NULL) fprintf (stderr, "DFCALL %ld: vertnbr=%ld veex=%d thrdnbr=%d passnbr=%ld\\n", callnum, (long) grafptr->s.vertnbr, grafptr->veextax != NULL, thrdnbr, (long) paraptr->passnbr); /* TEST INJECTION */\n', 1)
s = re.sub (r'^(\s*)threadBarrier \(descptr\);', r'\1TRACE ("barrier"); threadBarrier (descptr);', s, flags = re.M)
s = re.sub (r'^(\s*)threadReduce \(', r'\1TRACE ("reduce"); threadReduce (', s, flags = re.M)
s = re.sub (r'^(\s*)threadScan \(', r'\1TRACE ("scan"); threadScan (', s, flags = re.M)
s = s.replace ('  memFree (ielstax + vertbas);                    /* Free group leader of local arrays */', '  TRACE ("end of loop"); memFree (ielstax + vertbas);')
s = s.replace ('  memFree (loopdat.thrdtab);                      /* Free group leader */', '  fprintf (stderr, "DF END fronnbr=%ld\\n", (long) grafptr->fronnbr); memFree (loopdat.thrdtab);')
open (p, 'w').write (s)
PY
CF="$(grep '^CFLAGS' $BLD/src/Makefile.inc | cut -d= -f2-)"
gcc $CF -I$BLD/src/libscotch -I$BLD/include -shared -fPIC -o "$OUT" $TMP/df.c && echo "built $OUT"
rm -rf $TMP
