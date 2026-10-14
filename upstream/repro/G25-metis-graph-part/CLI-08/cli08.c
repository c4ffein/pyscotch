/* CLI-08: _SCOTCH_METIS_doubleToInt() scale factor blow-up on arbitrary target weights. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
#include "metis.h"
#include "../common/grid.h"
void _SCOTCH_METIS_doubleToInt (const SCOTCH_Num, const double * const, SCOTCH_Num * const);
int main (int argc, char * argv[])
{
  setvbuf (stdout, NULL, _IONBF, 0);
  int k = (argc > 1) ? atoi (argv[1]) : 6, seed = (argc > 2) ? atoi (argv[2]) : 1, i;
  double d[64], s = 0.0;
  SCOTCH_Num o[64];
  srand (seed);
  for (i = 0; i < k; i ++) { d[i] = 1.0 + rand () / (double) RAND_MAX; s += d[i]; }
  for (i = 0; i < k; i ++) d[i] /= s;
  _SCOTCH_METIS_doubleToInt (k, d, o);
  for (i = 0; i < k; i ++) printf ("%.6f -> %ld\n", d[i], (long) o[i]);
  {                                               /* Same weights through the public API */
    SCOTCH_Num n = 40 * 40, ncon = 1, nparts = k, objval = -1, options[METIS_NOPTIONS];
    SCOTCH_Num * xadj, * adjncy, * part = malloc (n * sizeof (SCOTCH_Num));
    int r;
    gridBuild (40, 40, 0, &xadj, &adjncy);
    METIS_SetDefaultOptions (options);
    r = METIS_PartGraphKway (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, d, NULL, options, &objval, part);
    printf ("METIS_PartGraphKway with these tpwgts: ret=%d objval=%ld\n", r, (long) objval);
    if (r == METIS_OK) {
      double load[64] = { 0 };
      int v;
      for (v = 0; v < n; v ++) load[part[v]] += 1.0;
      for (i = 0; i < k; i ++) printf ("  part %d: target %.4f actual %.4f\n", i, d[i], load[i] / n);
    }
  }
  return 0;
}
