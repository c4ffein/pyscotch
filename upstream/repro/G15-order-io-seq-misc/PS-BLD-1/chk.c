/* PS-BLD-1 harness: SCOTCH_graphOrderCheck() never looks at the user's
** direct permutation array.
** usage: chk <graph.grf>
** Computes an ordering with both permtab and peritab, then corrupts permtab
** (swaps two entries, so that it is no longer the inverse of peritab) and
** calls SCOTCH_graphOrderCheck(): pristine 7.0.17 returns 0.
*/
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        grafdat;
  SCOTCH_Ordering     ordedat;
  SCOTCH_Strat        stradat;
  SCOTCH_Num          vertnbr;
  SCOTCH_Num *        permtab;
  SCOTCH_Num *        peritab;
  SCOTCH_Num          tmp;
  FILE *              fileptr;
  int                 r1, r2, r3;

  SCOTCH_errorProg (argv[0]);
  SCOTCH_graphInit (&grafdat);
  if ((fileptr = fopen (argv[1], "r")) == NULL) return (3);
  if (SCOTCH_graphLoad (&grafdat, fileptr, -1, 0) != 0) return (3);
  fclose (fileptr);
  SCOTCH_graphData (&grafdat, NULL, &vertnbr, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
  permtab = malloc (vertnbr * sizeof (SCOTCH_Num));
  peritab = malloc (vertnbr * sizeof (SCOTCH_Num));
  SCOTCH_stratInit (&stradat);
  SCOTCH_graphOrderInit (&grafdat, &ordedat, permtab, peritab, NULL, NULL, NULL);
  if (SCOTCH_graphOrderCompute (&grafdat, &ordedat, &stradat) != 0) return (3);
  r1 = SCOTCH_graphOrderCheck (&grafdat, &ordedat);
  tmp = permtab[0]; permtab[0] = permtab[1]; permtab[1] = tmp; /* Corrupt direct permutation only */
  r2 = SCOTCH_graphOrderCheck (&grafdat, &ordedat);
  tmp = permtab[0]; permtab[0] = permtab[1]; permtab[1] = tmp; /* Restore */
  permtab[2] = -1;                                /* Out-of-range value */
  r3 = SCOTCH_graphOrderCheck (&grafdat, &ordedat);
  printf ("check(valid)=%d check(permtab swapped)=%d check(permtab out of range)=%d\n", r1, r2, r3);
  SCOTCH_graphOrderExit (&grafdat, &ordedat);
  SCOTCH_stratExit (&stradat);
  SCOTCH_graphExit (&grafdat);
  free (permtab);
  free (peritab);
  return ((r1 == 0) && (r2 != 0) && (r3 != 0)) ? 0 : 1;
}
