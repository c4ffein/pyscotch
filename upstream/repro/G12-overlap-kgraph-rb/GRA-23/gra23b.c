/* GRA-23 (b): SCOTCH_graphMapFixed with an isolated fixed vertex (weight 1)
** pinned to an invalid terminal (argv[1], e.g. 100) on cmplt(4):
** kgraphMapRbVfloMerge() stores an uninitialised domain; kgraphCost() then
** reads it (UBSan signed overflow) and the call returns 0.
** usage: gra23b termnum */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Arch         a;
  SCOTCH_Strat        s;
  SCOTCH_Num          n = 17;
  SCOTCH_Num          verttab[18];
  SCOTCH_Num          edgetab[80];
  SCOTCH_Num          parttab[17];
  SCOTCH_Num          e = 0;
  SCOTCH_Num          i;
  int                 r;

  for (i = 0; i < n; i ++) {                      /* 4x4 grid plus one isolated vertex */
    verttab[i] = e;
    if (i < 16) {
      int x = i % 4, y = i / 4;
      if (x > 0) edgetab[e ++] = i - 1;
      if (x < 3) edgetab[e ++] = i + 1;
      if (y > 0) edgetab[e ++] = i - 4;
      if (y < 3) edgetab[e ++] = i + 4;
    }
  }
  verttab[n] = e;
  SCOTCH_graphInit  (&g);
  SCOTCH_graphBuild (&g, 0, n, verttab, NULL, NULL, NULL, e, edgetab, NULL);
  for (i = 0; i < n; i ++)
    parttab[i] = -1;
  parttab[16] = atol (argv[1]);
  SCOTCH_archInit  (&a);
  SCOTCH_archCmplt (&a, 4);
  SCOTCH_stratInit (&s);
  r = SCOTCH_graphMapFixed (&g, &a, &s, parttab);
  printf ("ret=%d p[16]=%ld\n", r, (long) parttab[16]);
  return (0);
}
