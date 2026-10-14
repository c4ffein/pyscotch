/* CLI-10 / CLI-22 reproducer: call esmumps() on a small 2D grid graph (Fortran-based arrays)
** while the N-th malloc fails (LD_PRELOAD failmalloc.so, FAILMALLOC_AT=N).
** Prints the esmumps return value and how many nv/pe entries were written. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
#include "esmumps.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Num          g = (argc > 1) ? atoi (argv[1]) : 8;
  SCOTCH_Num          n = g * g;
  SCOTCH_Num *        pe   = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        len  = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        iw   = malloc (4 * n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        nv   = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        elen = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        last = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num          e = 1, u, i, j, r, nvw = 0, pew = 0;

  for (u = 0; u < n; u ++) {
    i = u % g; j = u / g;
    pe[u] = e;
    if (i > 0)     iw[e ++ - 1] = u;             /* 1-based neighbor numbers */
    if (i < g - 1) iw[e ++ - 1] = u + 2;
    if (j > 0)     iw[e ++ - 1] = u - g + 1;
    if (j < g - 1) iw[e ++ - 1] = u + g + 1;
    len[u] = e - pe[u];
    nv[u]  = -12345;                              /* Sentinels */
  }
  r = esmumps (n, e - 1, pe, e, len, iw, nv, elen, last);
  for (u = 0; u < n; u ++) {
    if (nv[u] != -12345) nvw ++;
    if (pe[u] <= 0)      pew ++;                  /* On output pe(i) <= 0 (0: root, <0: -father) */
  }
  printf ("esmumps returned %ld; nv written %ld/%ld, pe in output form %ld/%ld\n", (long) r, (long) nvw, (long) n, (long) pew, (long) n);
  return (0);
}
