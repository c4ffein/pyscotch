/* COR-18: print the first pseudo-random values of every MPI rank after
** SCOTCH_randomProc (rank) / SCOTCH_randomReset (), for the default seed
** (COMMON_RANDOM_FIXED_SEED -> 1) and for a user seed given as argv[1]. */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  int                 procnum, procnbr, i, r;
  char                strtab[256];
  char * ptr;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &procnum);
  MPI_Comm_size (MPI_COMM_WORLD, &procnbr);
  SCOTCH_randomProc (procnum);
  if (argc > 1)
    SCOTCH_randomSeed ((SCOTCH_Num) atol (argv[1]));
  SCOTCH_randomReset ();
  ptr = strtab;
  for (i = 0; i < 6; i ++)
    ptr += sprintf (ptr, " %10ld", (long) SCOTCH_randomVal (1000000000));
  for (r = 0; r < procnbr; r ++) {
    if (r == procnum)
      printf ("rank %d:%s\n", procnum, strtab);
    fflush (stdout);
    MPI_Barrier (MPI_COMM_WORLD);
  }
  MPI_Finalize ();
  return (0);
}
