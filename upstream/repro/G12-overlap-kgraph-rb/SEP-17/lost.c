/* SEP-17: count "lost" vertices of an overlap partition: separator vertices
** (-1) none of whose neighbours belongs to a part, so that the vertex belongs
** to no part at all. usage: lost vertnbr partnbr strategy|- [edgeless] */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Strat        s;
  SCOTCH_Num *        parttab;
  SCOTCH_Num          n     = atol (argv[1]);
  SCOTCH_Num          parts = atol (argv[2]);
  const char *        st    = argv[3];
  int                 edgeflag = (argc > 4) ? (atoi (argv[4]) == 0) : 1;
  SCOTCH_Num          baseval, vertnbr, * verttab, * vendtab, * edgetab;
  SCOTCH_Num          i, lostnbr = 0;
  int                 r;

  mkpath (&g, n, NULL, edgeflag);
  SCOTCH_stratInit (&s);
  if ((st[0] != '-') && (SCOTCH_stratGraphPartOvl (&s, st) != 0))
    return (2);
  parttab = malloc (n * sizeof (SCOTCH_Num));
  r = SCOTCH_graphPartOvl (&g, parts, &s, parttab);
  SCOTCH_graphData (&g, &baseval, &vertnbr, &verttab, &vendtab, NULL, NULL, NULL, &edgetab, NULL);
  printf ("ret=%d part:", r);
  for (i = 0; i < n; i ++) {
    printf (" %ld", (long) parttab[i]);
    if (parttab[i] == -1) {
      SCOTCH_Num e, ok = 0;
      for (e = verttab[i]; e < vendtab[i]; e ++)
        if (parttab[edgetab[e]] >= 0) ok = 1;
      if (! ok) lostnbr ++;
    }
  }
  printf ("  lost=%ld\n", (long) lostnbr);
  return ((r != 0) ? 1 : 0);
}
