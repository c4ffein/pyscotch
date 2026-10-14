/* API-21: SCOTCH_graphTabLoadSplit reads mappsorttab[mappfilenbr] after the last
** mapping entry has been consumed.
** Graph: 4-vertex path with vertex labels {0,0,1,2} (two vertices share
** label 0; neither SCOTCH_graphBuild nor SCOTCH_graphCheck rejects this).
** Mapping file: one entry, "0 5".
** Expected: parttab = {5,-1,-1,-1} (first vertex with label 0 gets the
** entry; the entry is consumed; no further match possible).
** 7.0.17 gives {5,0,-1,-1}: the second vertex of label 0 receives the
** "part" read from the cell following the mapping array.
*/

#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int SCOTCH_graphTabLoadSplit (const SCOTCH_Graph * const, SCOTCH_Num * const, FILE * const);

int
main (int argc, char * argv[])
{
  SCOTCH_Graph grafdat;
  SCOTCH_Num   verttab[5] = { 0, 1, 3, 5, 6 };
  SCOTCH_Num   edgetab[6] = { 1, 0, 2, 1, 3, 2 };
  SCOTCH_Num   vlbltab[4] = { 0, 0, 1, 2 };
  SCOTCH_Num   parttab[4];
  FILE *       stream;
  int          vertnum;
  int          o;

  SCOTCH_graphInit (&grafdat);
  if ((SCOTCH_graphBuild (&grafdat, 0, 4, verttab, NULL, NULL, vlbltab, 6, edgetab, NULL) != 0) ||
      (SCOTCH_graphCheck (&grafdat) != 0)) {
    fprintf (stderr, "cannot build graph\n");
    exit (EXIT_FAILURE);
  }

  stream = tmpfile ();
  fputs ("1\n0 5\n", stream);
  rewind (stream);
  if (SCOTCH_graphTabLoadSplit (&grafdat, parttab, stream) != 0) {
    fprintf (stderr, "graphTabLoad failed\n");
    exit (EXIT_FAILURE);
  }
  fclose (stream);

  o = ((parttab[0] != 5) || (parttab[1] != -1) || (parttab[2] != -1) || (parttab[3] != -1));
  printf ("parttab =");
  for (vertnum = 0; vertnum < 4; vertnum ++)
    printf (" %ld", (long) parttab[vertnum]);
  printf ("   expected: 5 -1 -1 -1   %s\n", o ? "FAIL" : "ok");

  SCOTCH_graphExit (&grafdat);
  return (o ? EXIT_FAILURE : EXIT_SUCCESS);
}
