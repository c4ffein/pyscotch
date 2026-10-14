#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char ** argv)
{
  int rank, ret;
  SCOTCH_Dgraph g; SCOTCH_Strat st; FILE * f; SCOTCH_Dordering o;
  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  f = (rank == 0) ? fopen (argv[1], "r") : NULL;
  if (SCOTCH_dgraphLoad (&g, f, -1, 0) != 0) MPI_Abort (MPI_COMM_WORLD, 1);
  if (f) fclose (f);
  SCOTCH_stratInit (&st);
  SCOTCH_dgraphOrderInit (&g, &o);
  ret = SCOTCH_dgraphOrderCompute (&g, &o, &st);
  printf ("rank %d compute ret=%d\n", rank, ret);
  const char * kind = argv[2];
  FILE * out = (rank == 0) ? fopen (argv[3], "w") : NULL;
  if (kind[0] == 'b') ret = SCOTCH_dgraphOrderSaveBlock (&g, &o, out);
  else if (kind[0] == 'm') ret = SCOTCH_dgraphOrderSaveMap (&g, &o, out);
  else if (kind[0] == 't') ret = SCOTCH_dgraphOrderSaveTree (&g, &o, out);
  else ret = SCOTCH_dgraphOrderSave (&g, &o, out);
  printf ("rank %d save(%s) ret=%d\n", rank, kind, ret);
  if (out) fclose (out);
  if (rank == 0 && kind[0] == 'c') { }
  SCOTCH_Num nb = SCOTCH_dgraphOrderCblkDist (&g, &o);
  printf ("rank %d CblkDist=%ld\n", rank, (long) nb);
  SCOTCH_dgraphOrderExit (&g, &o);
  SCOTCH_dgraphExit (&g);
  MPI_Finalize ();
  return 0;
}
