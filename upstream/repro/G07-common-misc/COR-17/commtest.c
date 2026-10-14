/* COR-17 / PS-COR-2: drive the large-count MPI wrappers of comm.c with an
** out-of-range count on ONE rank and see whether the other ranks hang.
** Needs a 64-bit Gnum build (sizeof (Gnum) != sizeof (int)).
** Usage: mpirun -np P ./commtest <case>
**   g1 : commGatherv, root's recvcnttab[1] overflows int (root-only check)
**   g2 : commGatherv, rank 1's sendcntnbr overflows int (local check, 7.0.17 "(2)")
**   s1 : commScatterv, root's sendcnttab[1] overflows int (root-only check)
**   s2 : commScatterv, rank 1's recvcntnbr overflows int (unchecked cast)
**   a1 : commAllgatherv, rank 1's sendcntnbr overflows int (unchecked implicit cast)
**   ok : all counts valid (sanity); s0 / a0: valid scatter / allgather (for malloc injection)
** Every rank prints "<rank> ret=<code>" when the wrapper returns; a rank
** that never prints is hung (run under timeout). */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include <dlfcn.h>
#include "module.h"
#include "common.h"
#include "comm.h"

#define BIGCNT ((Gnum) 1 << 33)                   /* Does not fit in an int */
#define SNDCNT ((Gnum) 1 << 22)                   /* 4 Mi elements: rendezvous-size message */

int
main (int argc, char * argv[])
{
  int                 procnum, procnbr, procidx;
  Gnum *              senddattab;
  Gnum *              recvdattab;
  Gnum *              cnttab;
  Gnum *              dsptab;
  Gnum                sendcnt, recvcnt;
  const char *        casestr = (argc > 1) ? argv[1] : "ok";
  int                 o;

  MPI_Init (&argc, &argv);
  {
    volatile long * armptr = (volatile long *) dlsym (RTLD_DEFAULT, "fi_armed"); /* Arm the LD_PRELOAD malloc fault injector if present */
    if (armptr != NULL)
      *armptr = 1;
  }
  MPI_Comm_rank (MPI_COMM_WORLD, &procnum);
  MPI_Comm_size (MPI_COMM_WORLD, &procnbr);
  if (procnum == 0)
    printf ("sizeof (Gnum) = %d, sizeof (int) = %d, case %s\n", (int) sizeof (Gnum), (int) sizeof (int), casestr);

  cnttab = malloc (procnbr * sizeof (Gnum));
  dsptab = malloc (procnbr * sizeof (Gnum));
  for (procidx = 0; procidx < procnbr; procidx ++) {
    cnttab[procidx] = SNDCNT;
    dsptab[procidx] = procidx * SNDCNT;
  }
  senddattab = malloc (SNDCNT * sizeof (Gnum));
  recvdattab = malloc (procnbr * SNDCNT * sizeof (Gnum));
  memset (senddattab, 0, SNDCNT * sizeof (Gnum));
  sendcnt = recvcnt = SNDCNT;

  if (strcmp (casestr, "g1") == 0) {
    if (procnum == 0) cnttab[1] = BIGCNT;
    o = commGatherv (senddattab, sendcnt, COMM_INT, recvdattab, cnttab, dsptab, COMM_INT, 0, MPI_COMM_WORLD);
  }
  else if (strcmp (casestr, "g2") == 0) {
    if (procnum == 1) sendcnt = BIGCNT;
    o = commGatherv (senddattab, sendcnt, COMM_INT, recvdattab, cnttab, dsptab, COMM_INT, 0, MPI_COMM_WORLD);
  }
  else if (strcmp (casestr, "s1") == 0) {
    if (procnum == 0) cnttab[1] = BIGCNT;
    o = commScatterv (recvdattab, cnttab, dsptab, COMM_INT, senddattab, recvcnt, COMM_INT, 0, MPI_COMM_WORLD);
  }
  else if (strcmp (casestr, "s2") == 0) {
    if (procnum == 1) recvcnt = BIGCNT;
    o = commScatterv (recvdattab, cnttab, dsptab, COMM_INT, senddattab, recvcnt, COMM_INT, 0, MPI_COMM_WORLD);
  }
  else if (strcmp (casestr, "a1") == 0) {
    if (procnum == 1) sendcnt = BIGCNT;
    o = commAllgatherv (senddattab, sendcnt, COMM_INT, recvdattab, cnttab, dsptab, COMM_INT, MPI_COMM_WORLD);
  }
  else if (strcmp (casestr, "s0") == 0)           /* Valid scatter: for allocation failure injection */
    o = commScatterv (recvdattab, cnttab, dsptab, COMM_INT, senddattab, recvcnt, COMM_INT, 0, MPI_COMM_WORLD);
  else if (strcmp (casestr, "a0") == 0)           /* Valid allgather: for allocation failure injection */
    o = commAllgatherv (senddattab, sendcnt, COMM_INT, recvdattab, cnttab, dsptab, COMM_INT, MPI_COMM_WORLD);
  else
    o = commGatherv (senddattab, sendcnt, COMM_INT, recvdattab, cnttab, dsptab, COMM_INT, 0, MPI_COMM_WORLD);

  printf ("%d ret=%d\n", procnum, o);
  fflush (stdout);
  MPI_Finalize ();
  return (0);
}
