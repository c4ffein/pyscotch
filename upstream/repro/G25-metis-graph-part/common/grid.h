/* Shared helper for the G25 reproducers: builds a w x h 4-neighbour grid
** graph in CSR form, with the given base value. */
#include <stdlib.h>
static void
gridBuild (int w, int h, SCOTCH_Num baseval, SCOTCH_Num ** xadjptr, SCOTCH_Num ** adjncyptr)
{
  int n = w * h, e = 0, i, j;
  SCOTCH_Num * xadj   = malloc ((n + 1) * sizeof (SCOTCH_Num));
  SCOTCH_Num * adjncy = malloc (4 * n * sizeof (SCOTCH_Num));
  for (j = 0; j < h; j ++) {
    for (i = 0; i < w; i ++) {
      xadj[j * w + i] = e + baseval;
      if (i > 0)     adjncy[e ++] = j * w + i - 1 + baseval;
      if (i < w - 1) adjncy[e ++] = j * w + i + 1 + baseval;
      if (j > 0)     adjncy[e ++] = (j - 1) * w + i + baseval;
      if (j < h - 1) adjncy[e ++] = (j + 1) * w + i + baseval;
    }
  }
  xadj[n] = e + baseval;
  *xadjptr = xadj; *adjncyptr = adjncy;
}
