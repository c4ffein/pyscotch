/* GRA-22 differential harness: block ordering 'b' on a vertex-weighted graph.
** usage: bl <strategy> [cmin] [mode]
**   mode 0 (default): 20x20 grid, loads 1+((i*7919)%23)
**   mode 1          : 20x20 grid, loads 1+i (strongly increasing)
**   mode 2          : path of 8 vertices, loads 1 1 1 1 1 1 0 0 (trailing zero loads)
** Prints, for every leaf column block, its weight (sum of loads of the vertices
** it contains, read through peritab), then min/max and how many blocks fall
** outside the documented [cmin, 2 cmin] span (last block may be smaller).
** Also checks that rangtab covers all vertices and that the ordering is valid.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph  grafdat;
  SCOTCH_Strat  stradat;
  SCOTCH_Num    n, e, i, cblknbr;
  SCOTCH_Num *  verttab, * edgetab, * velotab, * permtab, * peritab, * rangtab, * treetab;
  int           mode = (argc > 3) ? atoi (argv[3]) : 0;
  long          cmin = (argc > 2) ? atol (argv[2]) : 0;
  int           w = 20, h = 20;

  if (mode == 2) {
    n = 8; e = 2 * (n - 1);
    verttab = malloc ((n + 1) * sizeof (SCOTCH_Num)); edgetab = malloc (e * sizeof (SCOTCH_Num)); velotab = malloc (n * sizeof (SCOTCH_Num));
    for (i = 0, e = 0; i < n; i ++) { verttab[i] = e; if (i > 0) edgetab[e ++] = i - 1; if (i < n - 1) edgetab[e ++] = i + 1; velotab[i] = (i < 6) ? 1 : 0; }
    verttab[n] = e;
  }
  else {
    n = w * h; e = 0;
    verttab = malloc ((n + 1) * sizeof (SCOTCH_Num)); edgetab = malloc (4 * n * sizeof (SCOTCH_Num)); velotab = malloc (n * sizeof (SCOTCH_Num));
    for (i = 0; i < n; i ++) {
      int x = i % w, y = i / w;
      verttab[i] = e;
      if (x > 0) edgetab[e ++] = i - 1; if (x < w - 1) edgetab[e ++] = i + 1;
      if (y > 0) edgetab[e ++] = i - w; if (y < h - 1) edgetab[e ++] = i + w;
      velotab[i] = (mode == 1) ? (1 + i) : (1 + ((i * 7919) % 23));
    }
    verttab[n] = e;
  }
  SCOTCH_graphInit (&grafdat);
  if (SCOTCH_graphBuild (&grafdat, 0, n, verttab, NULL, velotab, NULL, e, edgetab, NULL) != 0) { puts ("build error"); return (3); }
  if (SCOTCH_graphCheck (&grafdat) != 0) { puts ("check error"); return (3); }
  permtab = malloc (n * sizeof (SCOTCH_Num)); peritab = malloc (n * sizeof (SCOTCH_Num));
  rangtab = malloc ((n + 1) * sizeof (SCOTCH_Num)); treetab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_stratInit (&stradat);
  if (SCOTCH_stratGraphOrder (&stradat, argv[1]) != 0) { puts ("strat error"); return (3); }
  {
    SCOTCH_Ordering ordedat;
    int r, c;
    SCOTCH_graphOrderInit (&grafdat, &ordedat, permtab, peritab, &cblknbr, rangtab, treetab);
    r = SCOTCH_graphOrderCompute (&grafdat, &ordedat, &stradat);
    c = SCOTCH_graphOrderCheck (&grafdat, &ordedat);
    printf ("ret=%d check=%d cblknbr=%ld\n", r, c, (long) cblknbr);
    SCOTCH_graphOrderExit (&grafdat, &ordedat);
    if (r != 0) return (2);
  }
  {
    long tot = 0, mn = 1L << 60, mx = 0, bad = 0, k, cover = 0, leaves = 0, lmax = 0;
    for (i = 0; i < n; i ++) { tot += velotab[i]; if (velotab[i] > lmax) lmax = velotab[i]; }
    printf ("total=%ld cmin=%ld blocks:", tot, cmin);
    for (k = 0; k < cblknbr; k ++) {
      long wsum = 0;
      for (i = rangtab[k]; i < rangtab[k + 1]; i ++) wsum += velotab[peritab[i]];
      cover += rangtab[k + 1] - rangtab[k];
      leaves ++;
      if (cblknbr <= 80) printf (" %ld", wsum);
      if (wsum < mn) mn = wsum;
      if (wsum > mx) mx = wsum;
      if ((cmin > 0) && (wsum > 2 * cmin + lmax)) bad ++; /* A block heavier than 2 cmin (plus one vertex) should have been split */
    }
    printf ("\nblocks=%ld min=%ld max=%ld heavier_than_2cmin+maxload=%ld covered=%ld/%ld rang_end=%ld\n", leaves, mn, mx, bad, cover, (long) n, (long) rangtab[cblknbr]);
    for (i = 0; i < n; i ++) if (peritab[permtab[i]] != i) { puts ("INVALID PERMUTATION"); return (4); }
    if (cover != n) { puts ("BLOCKS DO NOT COVER ALL VERTICES"); return (5); }
  }
  return (0);
}
