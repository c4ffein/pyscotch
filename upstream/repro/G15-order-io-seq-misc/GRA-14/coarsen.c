/* GRA-14 harness: SCOTCH_graphCoarsen / SCOTCH_graphCoarsenMatch under
** allocation-failure injection.
** usage: coarsen <graph.grf> <N> [match]
**   N      : fail the N-th allocation performed from the coarsening call on
**            (0 = no injection). Prints whether the injection fired, the
**            return value, and, when 0 is returned, checks the coarse graph
**            (SCOTCH_graphCheck) and frees it (SCOTCH_graphExit).
**   match  : exercise SCOTCH_graphCoarsenMatch instead.
*/
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

extern volatile long  inj_countdown;
extern volatile long  inj_fired;
extern volatile long  inj_calls;

int
main (int argc, char * argv[])
{
  SCOTCH_Graph  finegrafdat;
  SCOTCH_Graph  coargrafdat;
  SCOTCH_Num    vertnbr;
  SCOTCH_Num    coarvertnbr;
  SCOTCH_Num *  coarmulttab;
  SCOTCH_Num *  finematetab;
  FILE *        fileptr;
  long          n = atol (argv[2]);
  int           matchflag = (argc > 3);
  int           o;

  SCOTCH_errorProg (argv[0]);
  SCOTCH_graphInit (&finegrafdat);
  if ((fileptr = fopen (argv[1], "r")) == NULL) { puts ("cannot open"); return (3); }
  if (SCOTCH_graphLoad (&finegrafdat, fileptr, -1, 0) != 0) { puts ("cannot load"); return (3); }
  fclose (fileptr);
  SCOTCH_graphData (&finegrafdat, NULL, &vertnbr, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
  coarmulttab = malloc (2 * vertnbr * sizeof (SCOTCH_Num));
  finematetab = malloc (vertnbr * sizeof (SCOTCH_Num));
  SCOTCH_graphInit (&coargrafdat);

  inj_countdown = n;
  if (matchflag) {
    coarvertnbr = 1;
    o = SCOTCH_graphCoarsenMatch (&finegrafdat, &coarvertnbr, 0.8, SCOTCH_COARSENNONE, finematetab);
  }
  else
    o = SCOTCH_graphCoarsen (&finegrafdat, 1, 0.8, SCOTCH_COARSENNONE, &coargrafdat, coarmulttab);
  inj_countdown = 0;

  printf ("N=%ld fired=%ld calls=%ld ret=%d", n, inj_fired, inj_calls, o);
  if ((o == 0) && (! matchflag)) {
    SCOTCH_Num          cvertnbr;
    SCOTCH_Num          cedgenbr;

    SCOTCH_graphData (&coargrafdat, NULL, &cvertnbr, NULL, NULL, NULL, NULL, &cedgenbr, NULL, NULL);
    printf (" coarse: vertnbr=%ld edgenbr=%ld check=%d", (long) cvertnbr, (long) cedgenbr, SCOTCH_graphCheck (&coargrafdat));
    SCOTCH_graphExit (&coargrafdat);
  }
  if ((o == 0) && matchflag) {
    SCOTCH_Num          i;
    int                 bad = 0;

    for (i = 0; i < vertnbr; i ++)
      if ((finematetab[i] < 0) || (finematetab[i] >= vertnbr) || (finematetab[finematetab[i]] != i)) bad ++;
    printf (" match: coarvertnbr=%ld badmates=%d", (long) coarvertnbr, bad);
  }
  putchar ('\n');
  SCOTCH_graphExit (&finegrafdat);
  free (coarmulttab);
  free (finematetab);
  return ((o == 2) ? 0 : o);                      /* 2 = error properly reported */
}
