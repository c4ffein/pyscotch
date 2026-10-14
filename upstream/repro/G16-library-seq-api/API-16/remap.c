/* API-16 / PS-API-1 / API-03: SCOTCH_graphRemapView and SCOTCH_graphMapView.
** 8-vertex path mapped on a 8x1 2D mesh (a line of 8 processors).
**   new mapping {0,0,0,0,7,7,7,7}, old mapping {7,7,7,7,0,0,0,0}
** Every vertex migrates across the whole line: AvgMigrDist must be 7.
** CommDilat must print 1.000000 (7): the single cut edge (3,4) has dilation 7,
** which is 14 over the 14 arcs of the graph; the total dilation is 7;
** and parttab must come back untouched (API-03, fixed in 7.0.17).
** Run with base 0 and base 1 (base 1 overflows the old mapping array on 7.0.17).
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"

static void
pathBuild (SCOTCH_Graph * const grafptr, const int vertnbr, const int baseval)
{
  static SCOTCH_Num verttab[9];                   /* Static arrays: SCOTCH_graphBuild keeps pointers to them */
  static SCOTCH_Num edgetab[16];
  int               edgenbr = 0;
  int               vertnum;

  for (vertnum = 0; vertnum < vertnbr; vertnum ++) {
    verttab[vertnum] = baseval + edgenbr;
    if (vertnum > 0)
      edgetab[edgenbr ++] = baseval + vertnum - 1;
    if (vertnum < (vertnbr - 1))
      edgetab[edgenbr ++] = baseval + vertnum + 1;
  }
  verttab[vertnbr] = baseval + edgenbr;

  SCOTCH_graphInit (grafptr);
  if ((SCOTCH_graphBuild (grafptr, baseval, vertnbr, verttab, NULL, NULL, NULL, edgenbr, edgetab, NULL) != 0) ||
      (SCOTCH_graphCheck (grafptr) != 0)) {
    fprintf (stderr, "cannot build graph\n");
    exit (EXIT_FAILURE);
  }
}

static int
check (FILE * const stream, const char * const key, const char * const expected)
{
  char line[256];
  int  o = 1;

  rewind (stream);
  while (fgets (line, sizeof (line), stream) != NULL) {
    if (strncmp (line, key, strlen (key)) == 0) {
      line[strlen (line) - 1] = '\0';
      o = (strcmp (line + strlen (key), expected) != 0);
      printf ("  %-16s got: %-24s expected: %-24s %s\n", key + 2, line + strlen (key), expected, o ? "FAIL" : "ok");
    }
  }
  return (o);
}

int
main (int argc, char * argv[])
{
  SCOTCH_Graph   grafdat;
  SCOTCH_Arch    archdat;
  SCOTCH_Mapping mappdat;
  SCOTCH_Mapping mapodat;
  SCOTCH_Num     parttab[8] = { 0, 0, 0, 0, 7, 7, 7, 7 };
  SCOTCH_Num     parotab[8] = { 7, 7, 7, 7, 0, 0, 0, 0 };
  FILE *         stream;
  int            baseval;
  int            vertnum;
  int            o = 0;

  baseval = (argc > 1) ? atoi (argv[1]) : 0;
  printf ("base %d\n", baseval);

  pathBuild (&grafdat, 8, baseval);
  SCOTCH_archInit  (&archdat);
  SCOTCH_archMesh2 (&archdat, 8, 1);
  SCOTCH_graphMapInit (&grafdat, &mappdat, &archdat, parttab);
  SCOTCH_graphMapInit (&grafdat, &mapodat, &archdat, parotab);

  stream = tmpfile ();
  if (SCOTCH_graphRemapView (&grafdat, &mappdat, &mapodat, 1.0, NULL, stream) != 0) {
    fprintf (stderr, "graphRemapView failed\n");
    exit (EXIT_FAILURE);
  }
  o |= check (stream, "M\tCommDilat=",   "1.000000\t(7)"); /* Average dilation per edge is 14 / 14 arcs; total dilation 7 */
  o |= check (stream, "M\tMigrNbr=",     "8(100.000000 %)");
  o |= check (stream, "M\tAvgMigrDist=", "7.000000");
  o |= check (stream, "M\tPartDiam\t",   "min=3\tmax=3\tavg=3.000000");
  fclose (stream);

  for (vertnum = 0; vertnum < 8; vertnum ++) {    /* API-03: part arrays must be untouched */
    if ((parttab[vertnum] != ((vertnum < 4) ? 0 : 7)) ||
        (parotab[vertnum] != ((vertnum < 4) ? 7 : 0))) {
      printf ("  part arrays modified by view: FAIL\n");
      o = 1;
      break;
    }
  }

  SCOTCH_graphMapExit (&grafdat, &mapodat);
  SCOTCH_graphMapExit (&grafdat, &mappdat);
  SCOTCH_archExit  (&archdat);
  SCOTCH_graphExit (&grafdat);
  return (o ? EXIT_FAILURE : EXIT_SUCCESS);
}
