/* Driver for SCOTCH_dgraphOrderCompute() with fault injection (see fishim.c).
** usage: mpirun -np P ./orderfi graphfile [strategy|""] [mode]
** mode "rc"   (default): report the return code of every rank and stop.
** mode "user": behave like a user: if this rank's return code is 0, go on with
**              SCOTCH_dgraphOrderPerm() and SCOTCH_dgraphOrderSave() (rank 0 writes to /dev/null);
**              report their return codes. Ranks whose return code is not 0 skip them.
** mode "all":  call SCOTCH_dgraphOrderPerm() and SCOTCH_dgraphOrderSave() on every rank whatever
**              the return code (shows the behaviour of the downstream routines on a broken ordering).
** mode "check": after a successful ordering, gather the graph and the ordering on rank 0 and run
**              SCOTCH_graphOrderCheck() on them (validates the permutation and the block tree).
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
  int                 rank, o, op, os;
  FILE *              file;
  SCOTCH_Dgraph       g;
  SCOTCH_Dordering    ord;
  SCOTCH_Strat        strat;
  SCOTCH_Num          vertlocnbr;
  SCOTCH_Num *        permloctab;
  volatile long *     armed;
  long *              seen;
  const char *        mode;

  int                 thrdprolvl;

  MPI_Init_thread (&argc, &argv, MPI_THREAD_MULTIPLE, &thrdprolvl); /* As the src/check programs do (PT-Scotch may use threads with MPI) */
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  mode = (argc > 3) ? argv[3] : "rc";
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  file = (rank == 0) ? fopen (argv[1], "r") : NULL;
  if (SCOTCH_dgraphLoad (&g, file, -1, 0) != 0) { fprintf (stderr, "load failed\n"); return (2); }
  if (file != NULL) fclose (file);
  SCOTCH_stratInit (&strat);
  if ((argc > 2) && (argv[2][0] != '\0')) {
    if (SCOTCH_stratDgraphOrder (&strat, argv[2]) != 0) { fprintf (stderr, "strat failed\n"); return (2); }
  }
  SCOTCH_dgraphOrderInit (&g, &ord);
  SCOTCH_dgraphSize (&g, NULL, &vertlocnbr, NULL, NULL);
  permloctab = malloc ((vertlocnbr + 1) * sizeof (SCOTCH_Num));
  armed = dlsym (RTLD_DEFAULT, "fi_armed");
  seen  = dlsym (RTLD_DEFAULT, "fi_seen");
  if (armed != NULL) *armed = 1;
  o = SCOTCH_dgraphOrderCompute (&g, &ord, &strat);
  if (armed != NULL) *armed = 0;
  fprintf (stderr, "rank %d: order rc=%d seen=%ld\n", rank, o, (seen != NULL) ? *seen : -1L);
  if ((strcmp (mode, "all") == 0) || ((strcmp (mode, "user") == 0) && (o == 0))) {
    op = SCOTCH_dgraphOrderPerm (&g, &ord, permloctab);
    fprintf (stderr, "rank %d: perm rc=%d\n", rank, op);
    file = (rank == 0) ? fopen ("/dev/null", "w") : NULL;
    os = SCOTCH_dgraphOrderSave (&g, &ord, file);
    if (file != NULL) fclose (file);
    fprintf (stderr, "rank %d: save rc=%d\n", rank, os);
  }
  if (strcmp (mode, "check") == 0) {
    SCOTCH_Graph        cg;
    SCOTCH_Ordering     cord;
    SCOTCH_Num          vertglbnbr;
    SCOTCH_Num *        permtab;
    SCOTCH_Num *        peritab;
    int                 oc;

    SCOTCH_dgraphSize (&g, &vertglbnbr, NULL, NULL, NULL);
    SCOTCH_graphInit (&cg);
    if (SCOTCH_dgraphGather (&g, (rank == 0) ? &cg : NULL) != 0) { fprintf (stderr, "gather failed\n"); return (2); }
    oc = 0;
    if (rank == 0) {
      permtab = malloc (vertglbnbr * sizeof (SCOTCH_Num));
      peritab = malloc (vertglbnbr * sizeof (SCOTCH_Num));
      SCOTCH_graphOrderInit (&cg, &cord, permtab, peritab, NULL, NULL, NULL);
      oc = SCOTCH_dgraphOrderGather (&g, &ord, &cord);
      if (oc == 0)
        oc = SCOTCH_graphOrderCheck (&cg, &cord);
      fprintf (stderr, "rank 0: ordering check rc=%d\n", oc);
      SCOTCH_graphOrderExit (&cg, &cord);
      free (permtab); free (peritab);
      SCOTCH_graphExit (&cg);
    }
    else
      SCOTCH_dgraphOrderGather (&g, &ord, NULL);
  }
  SCOTCH_dgraphOrderExit (&g, &ord);
  SCOTCH_stratExit (&strat);
  SCOTCH_dgraphExit (&g);
  free (permloctab);
  MPI_Finalize ();
  return (0);                                     /* Exit code is always 0 so that mpirun does not kill the other processes before they report */
}
