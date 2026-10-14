/* CLI-02: METIS_PartGraphRecursive (v5 API) with ubvec == NULL. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
#include "metis.h"
#include "../common/grid.h"
int main (int argc, char * argv[])
{
  setvbuf (stdout, NULL, _IONBF, 0);
  SCOTCH_Num n = 40 * 40, ncon = 1, nparts = 4, objval = -1, options[METIS_NOPTIONS];
  SCOTCH_Num * xadj, * adjncy, * part = malloc (n * sizeof (SCOTCH_Num));
  int kway = (argc > 1 && argv[1][0] == 'k');
  int r;
  gridBuild (40, 40, 0, &xadj, &adjncy);
  METIS_SetDefaultOptions (options);
  r = kway ? METIS_PartGraphKway      (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, NULL, NULL, options, &objval, part)
           : METIS_PartGraphRecursive (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, NULL, NULL, options, &objval, part);
  printf ("%s: ret=%d objval=%ld\n", kway ? "Kway" : "Recursive", r, (long) objval);
  return (r == METIS_OK) ? 0 : 1;
}
