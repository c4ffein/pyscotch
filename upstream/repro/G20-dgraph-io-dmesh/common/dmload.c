/* dmload: load an auxiliary distributed mesh (file template with %r) through
** SCOTCH_dmeshLoad, build its dual graph with SCOTCH_dmeshDgraphDual, check it.
** usage: mpirun -np P ./dmload FILE-%r.adm [NOCONBR] [-b BASE]
** fishim.so is armed around dmeshLoad + dmeshDgraphDual.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  int                 rank, np, i, rc, rcd = -1, chk = -1;
  SCOTCH_Num          baseval = -1, noconbr = 1;
  SCOTCH_Dmesh        m;
  SCOTCH_Dgraph       g;
  FILE *              f;
  char                buf[1024];
  const char *        p;
  char *              q;
  volatile long *     armed;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  for (i = 2; i < argc; i ++) {
    if (strcmp (argv[i], "-b") == 0) baseval = atol (argv[++ i]);
    else noconbr = atol (argv[i]);
  }
  for (p = argv[1], q = buf; *p != '\0'; p ++) {
    if ((p[0] == '%') && (p[1] == 'r')) { q += sprintf (q, "%d", rank); p ++; }
    else *q ++ = *p;
  }
  *q = '\0';
  armed = (volatile long *) dlsym (RTLD_DEFAULT, "fi_armed");
  if ((f = fopen (buf, "r")) == NULL) {
    fprintf (stderr, "r%d: cannot open %s\n", rank, buf);
    MPI_Abort (MPI_COMM_WORLD, 2);
  }
  SCOTCH_dmeshInit (&m, MPI_COMM_WORLD);
  if (armed != NULL) *armed = 1;
  rc = SCOTCH_dmeshLoad (&m, f, baseval, 0);
  fclose (f);
  if (rc == 0) {
    SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
    rcd = SCOTCH_dmeshDgraphDual (&m, &g, noconbr);
    if (armed != NULL) *armed = 0;
    if (rcd == 0) {
      chk = SCOTCH_dgraphCheck (&g);
      SCOTCH_dgraphExit (&g);
    }
  }
  if (armed != NULL) *armed = 0;
  SCOTCH_dmeshExit (&m);
  fprintf (stderr, "r%d: load rc=%d dual rc=%d check=%d\n", rank, rc, rcd, chk);
  MPI_Finalize ();
  return ((rc != 0) || (rcd != 0) || (chk > 0)) ? 1 : 0;
}
