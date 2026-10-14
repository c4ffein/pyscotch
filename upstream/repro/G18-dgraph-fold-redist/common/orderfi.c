/* Driver for SCOTCH_dgraphOrderCompute() (nested dissection folds halo graphs through hdgraphFold2())
** with fault injection (see fishim.c). usage: mpirun -np P ./orderfi graphfile
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "scotch.h"
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  int                 rank, o;
  FILE *              file;
  SCOTCH_Dgraph       g;
  SCOTCH_Dordering    ord;
  SCOTCH_Strat        strat;
  volatile long *     armed;
  long *              seen;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  file = (rank == 0) ? fopen (argv[1], "r") : NULL;
  if (SCOTCH_dgraphLoad (&g, file, -1, 0) != 0) { fprintf (stderr, "load failed\n"); return (2); }
  if (file != NULL) fclose (file);
  SCOTCH_stratInit (&strat);
  SCOTCH_dgraphOrderInit (&g, &ord);
  armed = dlsym (RTLD_DEFAULT, "fi_armed");
  seen  = dlsym (RTLD_DEFAULT, "fi_seen");
  if (armed != NULL) *armed = 1;
  o = SCOTCH_dgraphOrderCompute (&g, &ord, &strat);
  if (armed != NULL) *armed = 0;
  fprintf (stderr, "rank %d: order rc=%d seen=%ld\n", rank, o, (seen != NULL) ? *seen : -1L);
  SCOTCH_dgraphOrderExit (&g, &ord);
  SCOTCH_stratExit (&strat);
  SCOTCH_dgraphExit (&g);
  MPI_Finalize ();
  return (o != 0);
}
