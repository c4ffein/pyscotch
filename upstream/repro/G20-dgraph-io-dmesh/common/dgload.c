/* dgload: load a distributed graph through SCOTCH_dgraphLoad and check it.
** usage: mpirun -np P ./dgload FILE [-d] [-2] [-b BASE] [-f FLAG]
**   FILE   : centralized graph file opened by rank 0 only; with -d, a
**            distributed file name template where "%r" is replaced by the rank.
**   -2     : perform a second load on the same communicator afterwards
**            (shows stray messages left by an aborted first load).
** Fault injection: the fishim.so LD_PRELOAD shim is armed (fi_armed = 1)
** around the first SCOTCH_dgraphLoad only.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <mpi.h>
#include "ptscotch.h"

static FILE *
openfile (const char * tmpl, int rank, int dist)
{
  char                buf[1024];
  const char *        p;
  char *              q;

  if (! dist)
    return ((rank == 0) ? fopen (tmpl, "r") : NULL);
  for (p = tmpl, q = buf; *p != '\0'; p ++) {
    if ((p[0] == '%') && (p[1] == 'r')) {
      q += sprintf (q, "%d", rank);
      p ++;
    }
    else
      *q ++ = *p;
  }
  *q = '\0';
  return (fopen (buf, "r"));
}

int
main (int argc, char * argv[])
{
  int                 rank, np, i, dist = 0, twice = 0, rc, rc2 = -1, chk = -1, flag = 0;
  SCOTCH_Num          baseval = -1, flagval = 0;
  SCOTCH_Dgraph       g;
  FILE *              f;
  volatile long *     armed;
  MPI_Status          st;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  for (i = 2; i < argc; i ++) {
    if (strcmp (argv[i], "-d") == 0) dist = 1;
    else if (strcmp (argv[i], "-2") == 0) twice = 1;
    else if (strcmp (argv[i], "-b") == 0) baseval = atol (argv[++ i]);
    else if (strcmp (argv[i], "-f") == 0) flagval = atol (argv[++ i]);
  }
  armed = (volatile long *) dlsym (RTLD_DEFAULT, "fi_armed");

  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  f = openfile (argv[1], rank, dist);
  if ((dist || (rank == 0)) && (f == NULL)) {
    fprintf (stderr, "r%d: cannot open file\n", rank);
    MPI_Abort (MPI_COMM_WORLD, 2);
  }
  if (armed != NULL) *armed = 1;
  rc = SCOTCH_dgraphLoad (&g, f, baseval, flagval);
  if (armed != NULL) *armed = 0;
  if (f != NULL) fclose (f);
  if (rc == 0) {
    chk = SCOTCH_dgraphCheck (&g);
    SCOTCH_dgraphExit (&g);
  }
  if (twice) {                                    /* Second load on the same communicator */
    MPI_Barrier (MPI_COMM_WORLD);
    MPI_Iprobe (MPI_ANY_SOURCE, MPI_ANY_TAG, MPI_COMM_WORLD, &flag, &st);
    if (flag) fprintf (stderr, "r%d: stray message pending before second load: src=%d tag=%d\n", rank, st.MPI_SOURCE, st.MPI_TAG);
    SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
    f = openfile (argv[1], rank, dist);
    rc2 = SCOTCH_dgraphLoad (&g, f, baseval, flagval);
    if (f != NULL) fclose (f);
    if (rc2 == 0) SCOTCH_dgraphExit (&g);
  }
  fprintf (stderr, "r%d: rc=%d check=%d rc2=%d\n", rank, rc, chk, rc2);
  MPI_Finalize ();
  return ((rc != 0) || (chk > 0)) ? 1 : 0;
}
