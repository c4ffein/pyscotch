/* GRA-02 public-API reproducer: SCOTCH_graphMap on a WxW grid onto cmplt(K) with a given strategy */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int
main (int argc, char * argv[])
{
  int w = (argc > 3) ? atoi (argv[3]) : 32, k = atoi (argv[1]);
  SCOTCH_Num n = (SCOTCH_Num) w * w, e = 0, i;
  SCOTCH_Num * vt = malloc ((n + 1) * sizeof (SCOTCH_Num));
  SCOTCH_Num * et = malloc (4 * n * sizeof (SCOTCH_Num));
  SCOTCH_Num * pt = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Graph g; SCOTCH_Arch a; SCOTCH_Strat s;
  for (i = 0; i < n; i ++) { int x = i % w, y = i / w; vt[i] = e;
    if (x > 0) et[e ++] = i - 1; if (x < w - 1) et[e ++] = i + 1; if (y > 0) et[e ++] = i - w; if (y < w - 1) et[e ++] = i + w; }
  vt[n] = e;
  SCOTCH_graphInit (&g);
  if (SCOTCH_graphBuild (&g, 0, n, vt, NULL, NULL, NULL, e, et, NULL) != 0) return (9);
  SCOTCH_archInit (&a); SCOTCH_archCmplt (&a, k);
  SCOTCH_stratInit (&s);
  if (SCOTCH_stratGraphMap (&s, argv[2]) != 0) { puts ("strat err"); return (3); }
  int r = SCOTCH_graphMap (&g, &a, &s, pt);
  SCOTCH_Num pmax = -1; for (i = 0; i < n; i ++) if (pt[i] > pmax) pmax = pt[i];
  printf ("ret=%d maxpart=%ld\n", r, (long) pmax);
  return (0);
}
