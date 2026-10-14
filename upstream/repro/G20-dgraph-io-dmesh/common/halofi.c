/* halofi: SCOTCH_dgraphSave of a labeled graph exercises dgraphHaloSync2.
** usage: mpirun -np P ./halofi FILE   (centralized grf on rank 0)
** Arms fishim around the save only.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char * argv[]) {
  int rank, np, rc, rcs = -1;
  SCOTCH_Dgraph g; FILE * f, * out;
  volatile long * armed;
  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  armed = (volatile long *) dlsym (RTLD_DEFAULT, "fi_armed");
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  f = (rank == 0) ? fopen (argv[1], "r") : NULL;
  rc = SCOTCH_dgraphLoad (&g, f, -1, 0);
  if (f != NULL) fclose (f);
  if (rc == 0) {
    out = fopen ("/dev/null", "w");
    if (armed != NULL) *armed = 1;
    rcs = SCOTCH_dgraphSave (&g, out);            /* calls dgraphHaloSync for labels */
    if (armed != NULL) *armed = 0;
    fclose (out);
    SCOTCH_dgraphExit (&g);
  }
  fprintf (stderr, "r%d: load rc=%d save rc=%d\n", rank, rc, rcs);
  MPI_Finalize ();
  return 0;
}
