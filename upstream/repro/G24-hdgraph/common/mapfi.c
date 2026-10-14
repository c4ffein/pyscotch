/* Driver for SCOTCH_dgraphMap(): every rank loads the target architecture file itself.
** usage: mpirun -np P ./mapfi graphfile tgtfile|cmplt:<n>
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "scotch.h"
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  int                 rank, o;
  FILE *              file;
  SCOTCH_Dgraph       g;
  SCOTCH_Arch         a;
  SCOTCH_Strat        strat;
  SCOTCH_Num          vertlocnbr;
  SCOTCH_Num *        partloctab;
  volatile long *     armed;

  int                 thrdprolvl;

  MPI_Init_thread (&argc, &argv, MPI_THREAD_MULTIPLE, &thrdprolvl); /* As the src/check programs do (PT-Scotch may use threads with MPI) */
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  file = (rank == 0) ? fopen (argv[1], "r") : NULL;
  if (SCOTCH_dgraphLoad (&g, file, -1, 0) != 0) { fprintf (stderr, "load failed\n"); return (2); }
  if (file != NULL) fclose (file);
  SCOTCH_archInit (&a);
  if (strncmp (argv[2], "cmplt:", 6) == 0)
    SCOTCH_archCmplt (&a, atoi (argv[2] + 6));
  else {
    file = fopen (argv[2], "r");
    if ((file == NULL) || (SCOTCH_archLoad (&a, file) != 0)) { fprintf (stderr, "arch load failed\n"); return (2); }
    fclose (file);
  }
  SCOTCH_stratInit (&strat);
  SCOTCH_dgraphSize (&g, NULL, &vertlocnbr, NULL, NULL);
  partloctab = malloc ((vertlocnbr + 1) * sizeof (SCOTCH_Num));
  armed = dlsym (RTLD_DEFAULT, "fi_armed");
  if (armed != NULL) *armed = 1;
  o = SCOTCH_dgraphMap (&g, &a, &strat, partloctab);
  if (armed != NULL) *armed = 0;
  fprintf (stderr, "rank %d: arch %s map rc=%d\n", rank, SCOTCH_archName (&a), o);
  SCOTCH_stratExit (&strat);
  SCOTCH_archExit (&a);
  SCOTCH_dgraphExit (&g);
  free (partloctab);
  MPI_Finalize ();
  return (0);                                     /* Exit code is always 0 so that mpirun does not kill the other processes before they report */
}
