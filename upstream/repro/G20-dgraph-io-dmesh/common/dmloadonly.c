/* DGR-15: dmeshInit + dmeshLoad + dmeshExit only (no dual build). LeakSanitizer
** should report the prelvrttab block from dmeshLoadAdm if it is not freed.
** usage: mpirun -np P ./dmloadonly FILE-%r.adm
*/
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char * argv[]) {
  int rank, rc; SCOTCH_Dmesh m; FILE * f;
  char buf[1024]; const char * p; char * q;
  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  for (p = argv[1], q = buf; *p; p ++) { if (p[0]=='%'&&p[1]=='r'){q+=sprintf(q,"%d",rank);p++;} else *q++=*p; }
  *q = '\0';
  f = fopen (buf, "r");
  SCOTCH_dmeshInit (&m, MPI_COMM_WORLD);
  rc = SCOTCH_dmeshLoad (&m, f, -1, 0);
  if (f) fclose (f);
  SCOTCH_dmeshExit (&m);
  fprintf (stderr, "r%d: load rc=%d\n", rank, rc);
  MPI_Finalize (); return 0;
}
