/* Driver for SCOTCH_dgraphRedist() with fault injection (see fishim.c).
** usage: mpirun -np P ./redistfi base nl  (ring of nl*P vertices, packs of 3 vertices to successive processes)
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
  int                 rank, np, base, nl, i, ne, o;
  long                N, lo;
  SCOTCH_Num *        vert;
  SCOTCH_Num *        edge;
  SCOTCH_Num *        part;
  SCOTCH_Dgraph       sg, dg;
  volatile long *     armed;
  long *              seen;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  base = atoi (argv[1]); nl = atoi (argv[2]);
  N = (long) nl * np; lo = (long) nl * rank;
  vert = malloc ((nl + 1) * sizeof (SCOTCH_Num)); edge = malloc ((2 * nl + 2) * sizeof (SCOTCH_Num)); part = malloc ((nl + 1) * sizeof (SCOTCH_Num));
  for (i = 0, ne = 0; i < nl; i ++) {
    long g = lo + i;
    vert[i] = base + ne; edge[ne ++] = base + (g + N - 1) % N; edge[ne ++] = base + (g + 1) % N;
    part[i] = (g / 3) % np;
  }
  vert[nl] = base + ne;
  SCOTCH_dgraphInit (&sg, MPI_COMM_WORLD);
  if (SCOTCH_dgraphBuild (&sg, base, nl, nl, vert, NULL, NULL, NULL, ne, ne, edge, NULL, NULL) != 0) return (2);
  SCOTCH_dgraphInit (&dg, MPI_COMM_WORLD);
  armed = dlsym (RTLD_DEFAULT, "fi_armed"); seen = dlsym (RTLD_DEFAULT, "fi_seen");
  if (armed != NULL) *armed = 1;
  o = SCOTCH_dgraphRedist (&sg, part, NULL, 0, 0, &dg);
  if (armed != NULL) *armed = 0;
  fprintf (stderr, "rank %d: redist rc=%d seen=%ld\n", rank, o, (seen != NULL) ? *seen : -1L);
  if (o == 0) {
    fprintf (stderr, "rank %d: redistributed check=%d\n", rank, SCOTCH_dgraphCheck (&dg));
    SCOTCH_dgraphExit (&dg);
  }
  SCOTCH_dgraphExit (&sg); free (vert); free (edge); free (part);
  MPI_Finalize ();
  return (o != 0);
}
