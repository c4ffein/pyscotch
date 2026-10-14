/* ghstfi base nl : SCOTCH_dgraphGhst() on a ring; FI_RANK/FI_NTH fail one allocation; then SCOTCH_dgraphExit(). */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
#include "../common/fi.h"
#include "../common/ring.h"
int main (int argc, char ** argv) {
  int rank, np, rc, b = atoi (argv[1]), nl = atoi (argv[2]);
  SCOTCH_Dgraph g;
  MPI_Init (&argc, &argv); MPI_Comm_rank (MPI_COMM_WORLD, &rank); MPI_Comm_size (MPI_COMM_WORLD, &np);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  ring_setup (rank, np, b, nl, 0);
  if (ring_build (&g, b, nl) != 0) { fprintf (stderr, "r%d setup failed\n", rank); MPI_Abort (MPI_COMM_WORLD, 2); }
  fi_arm (1);
  rc = SCOTCH_dgraphGhst (&g);
  fi_arm (0);
  fprintf (stderr, "r%d ghst rc=%d\n", rank, rc);
  if (rc == 0) { int ck = SCOTCH_dgraphCheck (&g); fprintf (stderr, "r%d check rc=%d\n", rank, ck); }
  SCOTCH_dgraphExit (&g);
  fprintf (stderr, "r%d exit done\n", rank);
  MPI_Finalize (); return (0);
}
