/* SEP-19 driver: run a bipartition with the greedy graph growing method
** through the non-exiting error handler, and report the return value of
** SCOTCH_graphPart(). Built against a SCOTCH_DEBUG_BGRAPH2 library in
** which bgraphBipartGg() makes its own graph data inconsistent on purpose
** (injected fault), the routine must report failure.
** Usage: sep19 <graph_file> */

#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (
int                 argc,
char *              argv[])
{
  SCOTCH_Graph        grafdat;
  SCOTCH_Strat        stradat;
  SCOTCH_Num          vertnbr;
  SCOTCH_Num *        parttab;
  FILE *              fileptr;
  int                 o;

  if (argc != 2)
    return (1);
  if ((fileptr = fopen (argv[1], "r")) == NULL)
    return (1);
  SCOTCH_graphInit (&grafdat);
  if (SCOTCH_graphLoad (&grafdat, fileptr, -1, 0) != 0)
    return (1);
  fclose (fileptr);
  SCOTCH_graphSize (&grafdat, &vertnbr, NULL);
  if ((parttab = malloc (vertnbr * sizeof (SCOTCH_Num))) == NULL)
    return (1);

  SCOTCH_randomReset ();
  SCOTCH_stratInit (&stradat);
  if (SCOTCH_stratGraphMap (&stradat, "r{sep=h{pass=20}}") != 0)
    return (1);
  o = SCOTCH_graphPart (&grafdat, 2, &stradat, parttab);
  printf ("SCOTCH_graphPart returned %d\n", o);

  SCOTCH_stratExit (&stradat);
  SCOTCH_graphExit (&grafdat);
  free (parttab);

  return (0);
}
