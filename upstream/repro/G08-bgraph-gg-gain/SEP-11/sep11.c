/* SEP-11 reproducer: bipartition a vertex-weighted complete graph with
** the greedy graph growing method on several threads, and print the
** final imbalance |compload0 - compload1| and the cut. On a complete
** graph with unit edge loads, all bipartitions with the same number of
** vertices in part 0 have the same cut, so threads often tie on
** communication load and the tie-breaking rule on imbalance decides.
** Usage: sep11 <vertnbr> <seed> */

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
  SCOTCH_Num          edgenbr;
  SCOTCH_Num *        verttab;
  SCOTCH_Num *        velotab;
  SCOTCH_Num *        edgetab;
  SCOTCH_Num *        parttab;
  SCOTCH_Num          vertnum;
  SCOTCH_Num          edgenum;
  SCOTCH_Num          loadtab[2];
  SCOTCH_Num          cutval;
  int                 seedval;

  if (argc != 3) {
    fprintf (stderr, "usage: %s vertnbr seed\n", argv[0]);
    return (1);
  }
  vertnbr = (SCOTCH_Num) atol (argv[1]);
  seedval = atoi (argv[2]);
  edgenbr = vertnbr * (vertnbr - 1);

  verttab = malloc ((vertnbr + 1) * sizeof (SCOTCH_Num));
  velotab = malloc (vertnbr       * sizeof (SCOTCH_Num));
  edgetab = malloc (edgenbr       * sizeof (SCOTCH_Num));
  parttab = malloc (vertnbr       * sizeof (SCOTCH_Num));
  if ((verttab == NULL) || (velotab == NULL) || (edgetab == NULL) || (parttab == NULL))
    return (1);

  for (vertnum = 0, edgenum = 0; vertnum < vertnbr; vertnum ++) { /* Complete graph */
    SCOTCH_Num          vertend;

    verttab[vertnum] = edgenum;
    velotab[vertnum] = 1 + ((vertnum * 7919) % 50); /* Pseudo-random vertex loads in [1, 50] */
    for (vertend = 0; vertend < vertnbr; vertend ++) {
      if (vertend != vertnum)
        edgetab[edgenum ++] = vertend;
    }
  }
  verttab[vertnbr] = edgenum;

  SCOTCH_randomSeed  (seedval);
  SCOTCH_randomReset ();

  SCOTCH_graphInit (&grafdat);
  if (SCOTCH_graphBuild (&grafdat, 0, vertnbr, verttab, NULL, velotab, NULL, edgenbr, edgetab, NULL) != 0)
    return (1);
  SCOTCH_stratInit (&stradat);
  if (SCOTCH_stratGraphMap (&stradat, "r{sep=h{pass=64}}") != 0)
    return (1);
  if (SCOTCH_graphPart (&grafdat, 2, &stradat, parttab) != 0)
    return (1);

  loadtab[0] = loadtab[1] = 0;
  for (vertnum = 0; vertnum < vertnbr; vertnum ++)
    loadtab[parttab[vertnum]] += velotab[vertnum];
  for (vertnum = 0, cutval = 0; vertnum < vertnbr; vertnum ++) {
    for (edgenum = verttab[vertnum]; edgenum < verttab[vertnum + 1]; edgenum ++) {
      if (parttab[edgetab[edgenum]] != parttab[vertnum])
        cutval ++;
    }
  }
  printf ("seed=%d cut=%ld imbalance=%ld\n", seedval, (long) (cutval / 2), (long) ((loadtab[0] > loadtab[1]) ? (loadtab[0] - loadtab[1]) : (loadtab[1] - loadtab[0])));

  SCOTCH_stratExit (&stradat);
  SCOTCH_graphExit (&grafdat);
  free (parttab);
  free (edgetab);
  free (velotab);
  free (verttab);

  return (0);
}
