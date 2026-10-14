/* SEP-01 / SEP-17: SCOTCH_graphPartOvl on a small path (or edgeless) graph.
** usage: partovl vertnbr partnbr strategy|- [edgeless]
** Prints the return value and the part array. */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Strat        s;
  SCOTCH_Num *        parttab;
  SCOTCH_Num          n     = (argc > 1) ? atol (argv[1]) : 6;
  SCOTCH_Num          parts = (argc > 2) ? atol (argv[2]) : 3;
  const char *        st    = (argc > 3) ? argv[3] : "r{sep=z}";
  int                 edgeflag = (argc > 4) ? (atoi (argv[4]) == 0) : 1;
  SCOTCH_Num          i;
  int                 r;

  mkpath (&g, n, NULL, edgeflag);
  SCOTCH_stratInit (&s);
  if ((st[0] != '-') && (SCOTCH_stratGraphPartOvl (&s, st) != 0)) {
    fprintf (stderr, "invalid strategy\n");
    return (2);
  }
  parttab = malloc (n * sizeof (SCOTCH_Num));
  for (i = 0; i < n; i ++)
    parttab[i] = -99;
  r = SCOTCH_graphPartOvl (&g, parts, &s, parttab);
  printf ("ret=%d part:", r);
  for (i = 0; i < n; i ++)
    printf (" %ld", (long) parttab[i]);
  printf ("\n");
  return ((r != 0) ? 1 : 0);
}
