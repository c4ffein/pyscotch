/* GRA-21: SCOTCH_graphMapFixed on a 16x16 grid, cmplt(4), with one fixed
** vertex pinned to an invalid terminal (argv[1], e.g. 100): the bipartition
** graph created by kgraphMapRbBgraph() is leaked on the error path.
** usage: gra21 termnum [arch]  with arch = c (cmplt, Part path) or h (hcub, Map path) */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Arch         a;
  SCOTCH_Strat        s;
  SCOTCH_Num          n = 256;
  SCOTCH_Num *        parttab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num          i;
  int                 r;

  mkgrid (&g, 16, 16, NULL);
  for (i = 0; i < n; i ++)
    parttab[i] = -1;
  parttab[5]   = atol (argv[1]);
  parttab[200] = 1;
  SCOTCH_archInit (&a);
  if ((argc > 2) && (argv[2][0] == 'h'))
    SCOTCH_archHcub (&a, 2);
  else
    SCOTCH_archCmplt (&a, 4);
  SCOTCH_stratInit (&s);
  r = SCOTCH_graphMapFixed (&g, &a, &s, parttab);
  printf ("ret=%d\n", r);
  SCOTCH_stratExit (&s);
  SCOTCH_archExit  (&a);
  SCOTCH_graphExit (&g);
  free (parttab);
  return (0);
}
