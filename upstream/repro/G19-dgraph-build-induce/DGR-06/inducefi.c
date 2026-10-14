/* inducefi base nl : SCOTCH_dgraphInducePart() keeping even local vertices of a ring; FI_RANK/FI_NTH fail one allocation. */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
#include "../common/fi.h"
#include "../common/ring.h"
int main (int argc, char ** argv) {
  int rank, np, rc, i, b = atoi (argv[1]), nl = atoi (argv[2]);
  SCOTCH_Num * part, keep = 0;
  SCOTCH_Dgraph g, ig;
  MPI_Init (&argc, &argv); MPI_Comm_rank (MPI_COMM_WORLD, &rank); MPI_Comm_size (MPI_COMM_WORLD, &np);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  ring_setup (rank, np, b, nl, 1);
  if (ring_build (&g, b, nl) != 0 || SCOTCH_dgraphGhst (&g) != 0) { fprintf (stderr, "r%d setup failed\n", rank); MPI_Abort (MPI_COMM_WORLD, 2); }
  part = malloc (nl * sizeof (SCOTCH_Num));
  for (i = 0; i < nl; i ++) { part[i] = i % 2; if (part[i] == 0) keep ++; }
  SCOTCH_dgraphInit (&ig, MPI_COMM_WORLD);
  fi_arm (1);
  rc = SCOTCH_dgraphInducePart (&g, part, 0, keep, &ig);
  fi_arm (0);
  fprintf (stderr, "r%d induce rc=%d\n", rank, rc);
  if (rc == 0) { int ck = SCOTCH_dgraphCheck (&ig); fprintf (stderr, "r%d check rc=%d\n", rank, ck); }
  SCOTCH_dgraphExit (&ig); SCOTCH_dgraphExit (&g);
  MPI_Finalize (); return (0);
}
