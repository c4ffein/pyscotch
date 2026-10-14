/* buildfi base nl : SCOTCH_dgraphBuild() of a ring; the fault injector (FI_RANK, FI_NTH) fails one allocation. */
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
  fi_arm (1);
  rc = ring_build (&g, b, nl);
  fi_arm (0);
  fprintf (stderr, "r%d build rc=%d\n", rank, rc);
  if (rc == 0) { int ck = SCOTCH_dgraphCheck (&g); fprintf (stderr, "r%d check rc=%d\n", rank, ck); }
  SCOTCH_dgraphExit (&g);
  MPI_Finalize (); return (0);
}
