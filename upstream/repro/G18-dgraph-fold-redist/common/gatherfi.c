/* Driver for SCOTCH_dgraphGather() with fault injection (see fishim.c).
** usage: mpirun -np P ./gatherfi mode base nl
**   mode: gather = rank 0 is root, others pass NULL
**         alias  = rank 0 is root, others pass their own SCOTCH_Dgraph (Fortran style)
** All ranks print their return value; rank 0 checks the centralized graph;
** all ranks check that their distributed graph is still consistent.
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
  int                 rank, np, base, nl, i, ne, o;
  long                N, lo;
  SCOTCH_Num *        vert;
  SCOTCH_Num *        edge;
  SCOTCH_Dgraph       sg;
  SCOTCH_Graph        cg;
  SCOTCH_Graph *      cgp;
  volatile long *     armed;
  long *              seen;
  const char *        mode = argv[1];

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  base = atoi (argv[2]);
  nl   = atoi (argv[3]);
  N  = (long) nl * np;
  lo = (long) nl * rank;
  vert = malloc ((nl + 1) * sizeof (SCOTCH_Num));
  edge = malloc ((2 * nl + 2) * sizeof (SCOTCH_Num));
  for (i = 0, ne = 0; i < nl; i ++) {
    long g = lo + i;
    vert[i] = base + ne;
    edge[ne ++] = base + (g + N - 1) % N;
    edge[ne ++] = base + (g + 1) % N;
  }
  vert[nl] = base + ne;
  SCOTCH_dgraphInit (&sg, MPI_COMM_WORLD);
  if (SCOTCH_dgraphBuild (&sg, base, nl, nl, vert, NULL, NULL, NULL, ne, ne, edge, NULL, NULL) != 0) {
    fprintf (stderr, "rank %d: build failed\n", rank);
    return (2);
  }
  SCOTCH_graphInit (&cg);
  if (rank == 0)
    cgp = &cg;
  else
    cgp = (strcmp (mode, "alias") == 0) ? (SCOTCH_Graph *) &sg : NULL;

  armed = dlsym (RTLD_DEFAULT, "fi_armed");
  seen  = dlsym (RTLD_DEFAULT, "fi_seen");
  if (armed != NULL) *armed = 1;
  o = SCOTCH_dgraphGather (&sg, cgp);
  if (armed != NULL) *armed = 0;
  fprintf (stderr, "rank %d: gather rc=%d seen=%ld\n", rank, o, (seen != NULL) ? *seen : -1L);

  if (SCOTCH_dgraphCheck (&sg) != 0)
    fprintf (stderr, "rank %d: distributed graph CORRUPTED after gather\n", rank);
  if ((o == 0) && (rank == 0)) {
    SCOTCH_Num          vertnbr, edgenbr;
    SCOTCH_graphSize (&cg, &vertnbr, &edgenbr);
    fprintf (stderr, "rank 0: centralized check=%d vertnbr=%ld edgenbr=%ld\n", SCOTCH_graphCheck (&cg), (long) vertnbr, (long) edgenbr);
    SCOTCH_graphExit (&cg);
  }
  SCOTCH_dgraphExit (&sg);
  free (vert); free (edge);
  MPI_Finalize ();
  return (o != 0);
}
