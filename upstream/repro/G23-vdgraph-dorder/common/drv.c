#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <stdint.h>
#include "ptscotch.h"
int main (int argc, char ** argv)
{
  int rank, np, ret;
  SCOTCH_Dgraph g; SCOTCH_Strat st; FILE * f;
  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank); MPI_Comm_size (MPI_COMM_WORLD, &np);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  f = (rank == 0) ? fopen (argv[1], "r") : NULL;
  if (SCOTCH_dgraphLoad (&g, f, -1, 0) != 0) { printf ("load fail\n"); MPI_Abort (MPI_COMM_WORLD, 1); }
  if (f) fclose (f);
  const char * mode = argv[2];
  SCOTCH_stratInit (&st);
  if (argc > 3 && argv[3][0]) {
    if (mode[0] == 'o') ret = SCOTCH_stratDgraphOrder (&st, argv[3]);
    else ret = SCOTCH_stratDgraphMap (&st, argv[3]);
    if (ret) { printf ("strat parse fail\n"); MPI_Abort (MPI_COMM_WORLD, 1); }
  }
  if (mode[0] == 'o') {
    SCOTCH_Dordering o; SCOTCH_dgraphOrderInit (&g, &o);
    ret = SCOTCH_dgraphOrderCompute (&g, &o, &st);
    printf ("rank %d: OrderCompute ret=%d\n", rank, ret); fflush (stdout);
    if (ret == 0) {
      SCOTCH_Num cb = SCOTCH_dgraphOrderCblkDist (&g, &o);
      printf ("rank %d: CblkDist=%ld\n", rank, (long) cb);
      SCOTCH_dgraphOrderExit (&g, &o);
    }
  } else {
    SCOTCH_Num parts = (argc > 4) ? atoi (argv[4]) : 4;
    SCOTCH_Num vl; SCOTCH_dgraphSize (&g, NULL, &vl, NULL, NULL);
    SCOTCH_Num * pt = calloc (vl + 1, sizeof (SCOTCH_Num));
    if (mode[0] == 'p') ret = SCOTCH_dgraphPart (&g, parts, &st, pt);
    else { SCOTCH_Arch a; SCOTCH_archInit (&a); SCOTCH_archCmplt (&a, parts); ret = SCOTCH_dgraphMap (&g, &a, &st, pt); }
    printf ("rank %d: Map/Part ret=%d\n", rank, ret); fflush (stdout);
  }
  SCOTCH_dgraphExit (&g);
  MPI_Finalize ();
  return 0;
}
