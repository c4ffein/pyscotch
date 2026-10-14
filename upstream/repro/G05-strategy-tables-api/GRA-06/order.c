/* GRA-06 / GRA-13: order a WxW grid with a user-given ordering strategy.
** peritab/permtab are pre-filled with a sentinel so that an unset ordering is visible. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (int argc, char * argv[])
{
  int           w = (argc > 2) ? atoi (argv[2]) : 8;
  SCOTCH_Num    n = (SCOTCH_Num) w * w, e = 0, i, bad;
  SCOTCH_Num *  vt = malloc ((n + 1) * sizeof (SCOTCH_Num));
  SCOTCH_Num *  et = malloc (4 * n * sizeof (SCOTCH_Num));
  SCOTCH_Num *  perm = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *  peri = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Graph  g;
  SCOTCH_Strat  s;
  int           r;

  for (i = 0; i < n; i ++) {
    int x = i % w, y = i / w;
    vt[i] = e;
    if (x > 0)     et[e ++] = i - 1;
    if (x < w - 1) et[e ++] = i + 1;
    if (y > 0)     et[e ++] = i - w;
    if (y < w - 1) et[e ++] = i + w;
  }
  vt[n] = e;
  for (i = 0; i < n; i ++)
    perm[i] = peri[i] = -7;                       /* Sentinel */

  SCOTCH_graphInit (&g);
  if (SCOTCH_graphBuild (&g, 0, n, vt, NULL, NULL, NULL, e, et, NULL) != 0)
    return (9);
  SCOTCH_stratInit (&s);
  if (SCOTCH_stratGraphOrder (&s, argv[1]) != 0) {
    puts ("strat err");
    return (3);
  }
  r = SCOTCH_graphOrder (&g, &s, perm, peri, NULL, NULL, NULL);
  for (i = 0, bad = 0; i < n; i ++)
    if ((peri[i] < 0) || (peri[i] >= n) || (perm[i] < 0) || (perm[i] >= n))
      bad ++;
  printf ("ret=%d peri[0]=%ld perm[0]=%ld invalid=%ld\n", r, (long) peri[0], (long) perm[0], (long) bad);
  SCOTCH_stratExit (&s);
  SCOTCH_graphExit (&g);
  free (vt);
  free (et);
  free (perm);
  free (peri);
  return ((r != 0) || (bad != 0));
}
