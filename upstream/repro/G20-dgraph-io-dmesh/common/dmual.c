/* DGR-20: np=1, 100 elements all sharing node 0 -> one element has 99 dual
** neighbours > 64 hash slots, forcing dmeshDgraphDualHashEdgeResize().
** Arms the realloc-fail shim (fi_armed) around SCOTCH_dmeshDgraphDual only.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char * argv[]) {
  int ne = (argc > 1) ? atoi (argv[1]) : 100, i, rc;
  volatile long * armed = (volatile long *) dlsym (RTLD_DEFAULT, "fi_armed");
  SCOTCH_Num * vel, * eel;
  SCOTCH_Dmesh m; SCOTCH_Dgraph g;
  MPI_Init (&argc, &argv);
  vel = malloc ((ne + 1) * sizeof (*vel)); eel = malloc (ne * sizeof (*eel));
  for (i = 0; i <= ne; i ++) vel[i] = i;
  for (i = 0; i < ne; i ++) eel[i] = 0;
  SCOTCH_dmeshInit (&m, MPI_COMM_WORLD);
  rc = SCOTCH_dmeshBuildAdm (&m, 0, ne, vel, ne, eel, 1);
  fprintf (stderr, "BuildAdm rc=%d\n", rc);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  if (armed != NULL) *armed = 1;
  rc = SCOTCH_dmeshDgraphDual (&m, &g, 1);
  if (armed != NULL) *armed = 0;
  fprintf (stderr, "DgraphDual rc=%d\n", rc);
  MPI_Finalize (); return 0;
}
