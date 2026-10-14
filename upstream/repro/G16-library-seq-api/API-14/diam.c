/* API-14: part pseudo-diameter in SCOTCH_graphMapView.
** Builds small path graphs with base 0 and base 1, maps them by hand on a
** complete-graph architecture and prints the PartDiam line of the view.
** Expected (true graph-theoretic values): see README.
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
run (const char * const title, const int vertnbr, const int baseval, SCOTCH_Num * const parttab, const int partnbr, const char * const expected)
{
  SCOTCH_Graph   grafdat;
  SCOTCH_Arch    archdat;
  SCOTCH_Mapping mappdat;
  FILE *         stream;
  char           line[256];
  int            o = 1;

  pathBuild (&grafdat, vertnbr, baseval);
  SCOTCH_archInit  (&archdat);
  SCOTCH_archCmplt (&archdat, partnbr);
  SCOTCH_graphMapInit (&grafdat, &mappdat, &archdat, parttab);

  stream = tmpfile ();
  if (SCOTCH_graphMapView (&grafdat, &mappdat, stream) != 0) {
    fprintf (stderr, "graphMapView failed\n");
    exit (EXIT_FAILURE);
  }
  rewind (stream);
  while (fgets (line, sizeof (line), stream) != NULL) {
    if (strncmp (line, "M\tPartDiam", 10) == 0) {
      line[strlen (line) - 1] = '\0';
      o = (strcmp (line + 11, expected) != 0);
      printf ("%-44s got: %s   expected: %s   %s\n", title, line + 11, expected, o ? "FAIL" : "ok");
    }
  }
  fclose (stream);

  SCOTCH_graphMapExit (&grafdat, &mappdat);
  SCOTCH_archExit  (&archdat);
  SCOTCH_graphExit (&grafdat);
  return (o);
}

int
main (void)
{
  SCOTCH_Num p0[4] = { 0, 0, 0, 0 };
  SCOTCH_Num p1[4] = { 0, 0, 0, 0 };
  SCOTCH_Num p2[4] = { 0, 0, 1, 1 };
  SCOTCH_Num p3[4] = { 0, 0, 1, 1 };
  SCOTCH_Num p4[4] = { 0, 1, 0, 1 };
  SCOTCH_Num p5[2] = { 0, 1 };
  SCOTCH_Num p6[2] = { 0, 1 };
  int        o = 0;

  o |= run ("path4 base0, one part (diam 3)",         4, 0, p0, 1, "min=3\tmax=3\tavg=3.000000");
  o |= run ("path4 base1, one part (diam 3)",         4, 1, p1, 1, "min=3\tmax=3\tavg=3.000000");
  o |= run ("path4 base0, {0,0,1,1} (diam 1,1)",      4, 0, p2, 2, "min=1\tmax=1\tavg=1.000000");
  o |= run ("path4 base1, {0,0,1,1} (diam 1,1)",      4, 1, p3, 2, "min=1\tmax=1\tavg=1.000000");
  o |= run ("path4 base0, {0,1,0,1} (2 comps/part)",  4, 0, p4, 2, "min=1\tmax=1\tavg=1.000000"); /* Two singletons chained by one virtual edge */
  o |= run ("path2 base0, {0,1} (diam 0,0)",          2, 0, p5, 2, "min=0\tmax=0\tavg=0.000000");
  o |= run ("path2 base1, {0,1} (diam 0,0)",          2, 1, p6, 2, "min=0\tmax=0\tavg=0.000000");

  return (o ? EXIT_FAILURE : EXIT_SUCCESS);
}
