/* gridparm dimx dimy dimz incr : SCOTCH_dgraphBuildGrid3D() with the given parameters (public API, release build). */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char ** argv) {
  int rank, rc;
  SCOTCH_Dgraph g;
  MPI_Init (&argc, &argv); MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  rc = SCOTCH_dgraphBuildGrid3D (&g, 0, atol (argv[1]), atol (argv[2]), atol (argv[3]), atol (argv[4]), 0);
  fprintf (stderr, "r%d grid3d(%s,%s,%s,incr %s) rc=%d\n", rank, argv[1], argv[2], argv[3], argv[4], rc);
  if (rc == 0) fprintf (stderr, "r%d check rc=%d\n", rank, SCOTCH_dgraphCheck (&g));
  SCOTCH_dgraphExit (&g); MPI_Finalize (); return (0);
}
