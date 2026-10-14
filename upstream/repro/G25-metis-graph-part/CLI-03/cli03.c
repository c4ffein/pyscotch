/* CLI-03: ubvec[0] (a METIS ratio such as 1.05) handed to Scotch as a deviation. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
#include "metis.h"
#include "../common/grid.h"
#include "../common/metrics.h"
int main (int argc, char * argv[])
{
  setvbuf (stdout, NULL, _IONBF, 0);
  SCOTCH_Num n = 40 * 40, ncon = 1, nparts = 4, objval = -1, options[METIS_NOPTIONS];
  SCOTCH_Num * xadj, * adjncy, * part = malloc (n * sizeof (SCOTCH_Num)), * vwgt = malloc (n * sizeof (SCOTCH_Num));
  const double ubtab[] = { 1.001, 1.01, 1.03, 1.05, 1.3 };
  int u, k, v;
  srand (1);
  for (v = 0; v < n; v ++) vwgt[v] = 1 + rand () % 10;
  gridBuild (40, 40, 0, &xadj, &adjncy);
  METIS_SetDefaultOptions (options);
  for (k = 0; k < 2; k ++) {
    for (u = 0; u < 6; u ++) {
      double ub = (u == 5) ? 0.0 : ubtab[u];
      const double * ubvec = (u == 5) ? NULL : &ub;
      int r;
      SCOTCH_randomReset ();
      r = (k == 0) ? METIS_PartGraphKway      (&n, &ncon, xadj, adjncy, vwgt, NULL, NULL, &nparts, NULL, ubvec, options, &objval, part)
                   : METIS_PartGraphRecursive (&n, &ncon, xadj, adjncy, vwgt, NULL, NULL, &nparts, NULL, ubvec, options, &objval, part);
      if (r != METIS_OK) { printf ("%s ubvec=%s: ret=%d\n", k ? "Recursive" : "Kway", ubvec ? "set" : "NULL", r); continue; }
      printf ("%-9s ubvec=%-5g ret=%d cut=%4ld imbalance=%.4f (max part load / ideal)\n", k ? "Recursive" : "Kway", ub, r, (long) objval,
              imbalCompute (n, 0, vwgt, 1, 0, nparts, NULL, part));
    }
  }
  return 0;
}
