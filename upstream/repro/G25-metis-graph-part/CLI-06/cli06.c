/* CLI-06: options[] filled with -1 (METIS "default") used as base value. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"
#include "metis.h"
#include "../common/grid.h"
int main (int argc, char * argv[])
{
  setvbuf (stdout, NULL, _IONBF, 0);
  SCOTCH_Num n = 40 * 40, ncon = 1, nparts = 4, objval = -1, options[METIS_NOPTIONS];
  SCOTCH_Num * xadj, * adjncy, * part = malloc (n * sizeof (SCOTCH_Num)), * perm = malloc (n * sizeof (SCOTCH_Num)), * iperm = malloc (n * sizeof (SCOTCH_Num));
  const char * mode = (argc > 1) ? argv[1] : "kway";
  int i, r;
  gridBuild (40, 40, 0, &xadj, &adjncy);
  for (i = 0; i < METIS_NOPTIONS; i ++) options[i] = -1;  /* What real METIS_SetDefaultOptions() does */
  if (!strcmp (mode, "kway"))
    r = METIS_PartGraphKway (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, NULL, NULL, options, &objval, part);
  else if (!strcmp (mode, "rec"))
    r = METIS_PartGraphRecursive (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, NULL, NULL, options, &objval, part);
  else if (!strcmp (mode, "nodend"))
    r = METIS_NodeND (&n, xadj, adjncy, NULL, options, perm, iperm);
  else if (!strcmp (mode, "num2")) {               /* NUMBERING = 2: neither 0 nor 1 */
    METIS_SetDefaultOptions (options); options[METIS_OPTION_NUMBERING] = 2;
    r = METIS_PartGraphKway (&n, &ncon, xadj, adjncy, NULL, NULL, NULL, &nparts, NULL, NULL, options, &objval, part);
  }
  else { fprintf (stderr, "bad mode\n"); return 2; }
  printf ("%s: ret=%d objval=%ld part[0]=%ld\n", mode, r, (long) objval, (long) part[0]);
  return (r == METIS_OK) ? 0 : 1;
}
