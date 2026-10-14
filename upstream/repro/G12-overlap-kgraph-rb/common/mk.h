/* Small helpers shared by the G12 reproducers: build a path or a 2D grid graph. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"

static void
mkpath (SCOTCH_Graph * const g, const SCOTCH_Num n, const SCOTCH_Num * const velotab, const int edgeflag)
{
  SCOTCH_Num * verttab = malloc ((n + 1) * sizeof (SCOTCH_Num));
  SCOTCH_Num * edgetab = malloc ((2 * n + 1) * sizeof (SCOTCH_Num));
  SCOTCH_Num   e = 0;
  SCOTCH_Num   i;

  for (i = 0; i < n; i ++) {
    verttab[i] = e;
    if (edgeflag) {
      if (i > 0)       edgetab[e ++] = i - 1;
      if (i < (n - 1)) edgetab[e ++] = i + 1;
    }
  }
  verttab[n] = e;
  SCOTCH_graphInit (g);
  if (SCOTCH_graphBuild (g, 0, n, verttab, NULL, (SCOTCH_Num *) velotab, NULL, e, edgetab, NULL) != 0) {
    fprintf (stderr, "mkpath: graphBuild failed\n");
    exit (9);
  }
}

static void
mkgrid (SCOTCH_Graph * const g, const int w, const int h, const SCOTCH_Num * const velotab)
{
  SCOTCH_Num   n = (SCOTCH_Num) w * h;
  SCOTCH_Num * verttab = malloc ((n + 1) * sizeof (SCOTCH_Num));
  SCOTCH_Num * edgetab = malloc (4 * n * sizeof (SCOTCH_Num));
  SCOTCH_Num   e = 0;
  SCOTCH_Num   i;

  for (i = 0; i < n; i ++) {
    int x = i % w, y = i / w;
    verttab[i] = e;
    if (x > 0)       edgetab[e ++] = i - 1;
    if (x < (w - 1)) edgetab[e ++] = i + 1;
    if (y > 0)       edgetab[e ++] = i - w;
    if (y < (h - 1)) edgetab[e ++] = i + w;
  }
  verttab[n] = e;
  SCOTCH_graphInit (g);
  if (SCOTCH_graphBuild (g, 0, n, verttab, NULL, (SCOTCH_Num *) velotab, NULL, e, edgetab, NULL) != 0) {
    fprintf (stderr, "mkgrid: graphBuild failed\n");
    exit (9);
  }
}
