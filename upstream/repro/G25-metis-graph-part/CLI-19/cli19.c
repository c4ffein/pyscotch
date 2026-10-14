/* CLI-19: objective chosen from vsize instead of options[METIS_OPTION_OBJTYPE]. */
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
  SCOTCH_Num * xadj, * adjncy, * part = malloc (n * sizeof (SCOTCH_Num)), * vsize = malloc (n * sizeof (SCOTCH_Num));
  int v, r, k;
  for (v = 0; v < n; v ++) vsize[v] = 1 + (v % 7);
  gridBuild (40, 40, 0, &xadj, &adjncy);
  for (k = 0; k < 2; k ++) {
    const char * name = k ? "Recursive" : "Kway";
    METIS_SetDefaultOptions (options);
    options[METIS_OPTION_OBJTYPE] = METIS_OBJTYPE_VOL;  /* VOL, no vsize: expect objval == volume with unit sizes */
    r = k ? METIS_PartGraphRecursive (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, NULL, NULL, options, &objval, part)
          : METIS_PartGraphKway      (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, NULL, NULL, options, &objval, part);
    printf ("%-9s OBJTYPE=VOL vsize=NULL : ret=%d objval=%ld | true cut=%ld true volume(unit)=%ld\n", name, r, (long) objval,
            (long) cutCompute (n, 0, xadj, adjncy, NULL, part), (long) volCompute (n, 0, xadj, adjncy, NULL, nparts, part));
    options[METIS_OPTION_OBJTYPE] = METIS_OBJTYPE_CUT;  /* CUT, with vsize: expect objval == cut */
    r = k ? METIS_PartGraphRecursive (&n, &ncon, xadj, adjncy, NULL, vsize, NULL, &nparts, NULL, NULL, options, &objval, part)
          : METIS_PartGraphKway      (&n, &ncon, xadj, adjncy, NULL, vsize, NULL, &nparts, NULL, NULL, options, &objval, part);
    printf ("%-9s OBJTYPE=CUT vsize=set  : ret=%d objval=%ld | true cut=%ld true volume(vsize)=%ld\n", name, r, (long) objval,
            (long) cutCompute (n, 0, xadj, adjncy, NULL, part), (long) volCompute (n, 0, xadj, adjncy, vsize, nparts, part));
    options[METIS_OPTION_OBJTYPE] = METIS_OBJTYPE_VOL;  /* VOL, with vsize: expect objval == volume */
    r = k ? METIS_PartGraphRecursive (&n, &ncon, xadj, adjncy, NULL, vsize, NULL, &nparts, NULL, NULL, options, &objval, part)
          : METIS_PartGraphKway      (&n, &ncon, xadj, adjncy, NULL, vsize, NULL, &nparts, NULL, NULL, options, &objval, part);
    printf ("%-9s OBJTYPE=VOL vsize=set  : ret=%d objval=%ld | true cut=%ld true volume(vsize)=%ld\n", name, r, (long) objval,
            (long) cutCompute (n, 0, xadj, adjncy, NULL, part), (long) volCompute (n, 0, xadj, adjncy, vsize, nparts, part));
  }
  return 0;
}
