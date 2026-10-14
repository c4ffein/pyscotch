/* CLI-07: ncon = 2, interleaved vwgt, strided tpwgts (sequential METIS v5). */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
#include "metis.h"
#include "../common/grid.h"
#include "../common/metrics.h"
int main (int argc, char * argv[])
{
  setvbuf (stdout, NULL, _IONBF, 0);
  SCOTCH_Num n = 40 * 40, ncon = 2, nparts = 4, objval = -1, options[METIS_NOPTIONS];
  SCOTCH_Num * xadj, * adjncy, * part = malloc (n * sizeof (SCOTCH_Num)), * vwgt = malloc (n * ncon * sizeof (SCOTCH_Num));
  double tpwgts[8] = { 0.10, 0.5, 0.20, 0.5, 0.30, 0.0, 0.40, 0.0 }; /* part i, constraint j at [i * ncon + j] */
  double ub[2] = { 1.03, 1.03 };
  int v, r, p;
  srand (1);
  for (v = 0; v < n; v ++) { vwgt[v * 2] = 1 + rand () % 10; vwgt[v * 2 + 1] = 1000 + v; }
  gridBuild (40, 40, 0, &xadj, &adjncy);
  METIS_SetDefaultOptions (options);
  r = METIS_PartGraphKway (&n, &ncon, xadj, adjncy, vwgt, NULL, NULL, &nparts, tpwgts, ub, options, &objval, part);
  printf ("ret=%d cut=%ld\n", r, (long) objval);
  if (r != METIS_OK) return 1;
  for (p = 0; p < nparts; p ++) {
    double l0 = 0, l1 = 0, lx = 0, t0 = 0, t1 = 0, tx = 0;
    for (v = 0; v < n; v ++) { t0 += vwgt[2 * v]; t1 += vwgt[2 * v + 1]; tx += vwgt[v]; if (part[v] == p) { l0 += vwgt[2 * v]; l1 += vwgt[2 * v + 1]; lx += vwgt[v]; } }
    printf ("part %d: target0=%.2f constraint0=%.4f constraint1=%.4f as-read-by-scotch(vwgt[v])=%.4f\n", p, tpwgts[2 * p], l0 / t0, l1 / t1, lx / tx);
  }
  printf ("imbalance on constraint 0 (max load/target): %.4f (requested <= 1.03)\n", imbalCompute (n, 0, vwgt, 2, 0, nparts, tpwgts, part));
  return 0;
}
