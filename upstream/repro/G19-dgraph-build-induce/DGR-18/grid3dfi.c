/* grid3dfi base incrval : SCOTCH_dgraphBuildGrid3D (4x4x2); FI_RANK/FI_NTH fail one allocation; then SCOTCH_dgraphExit(). */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
#include "../common/fi.h"
int main (int argc, char ** argv) {
  int rank, rc, b = atoi (argv[1]), incr = atoi (argv[2]);
  SCOTCH_Dgraph g;
  MPI_Init (&argc, &argv); MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  fi_arm (1);
  rc = SCOTCH_dgraphBuildGrid3D (&g, b, 4, 4, 2, incr, 0);
  fi_arm (0);
  fprintf (stderr, "r%d grid3d rc=%d\n", rank, rc);
  if (rc == 0) { int ck = SCOTCH_dgraphCheck (&g); fprintf (stderr, "r%d check rc=%d\n", rank, ck); }
  SCOTCH_dgraphExit (&g);
  fprintf (stderr, "r%d exit done\n", rank);
  MPI_Finalize (); return (0);
}
