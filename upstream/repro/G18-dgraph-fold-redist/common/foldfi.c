/* Driver for dgraphFold() with fault injection (see fishim.c).
** usage: mpirun -np P ./foldfi partval base nl [velo] [edlo] [data]
** Builds a ring of nl*P vertices, block-distributed, then folds it onto part partval.
** Receivers check the folded graph; all ranks print their return value.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "module.h"
#include "common.h"
#include "graph.h"
#include "dgraph.h"
#include "scotch.h"
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  int                 rank, np;
  int                 partval, base, nl, velo, edlo, data;
  Gnum                N, lo, i, ne;
  Gnum *              vert;
  Gnum *              edge;
  Gnum *              vlod = NULL;
  Gnum *              elod = NULL;
  Gnum *              dat  = NULL;
  Gnum *              flddat = NULL;
  SCOTCH_Dgraph       sg;
  Dgraph              fg;
  Dgraph *            g;
  int                 o;
  volatile long *     armed;
  long *              seen;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  partval = atoi (argv[1]);
  base    = atoi (argv[2]);
  nl      = atoi (argv[3]);
  velo    = (argc > 4) ? atoi (argv[4]) : 0;
  edlo    = (argc > 5) ? atoi (argv[5]) : 0;
  data    = (argc > 6) ? atoi (argv[6]) : 0;

  N  = (Gnum) nl * np;
  lo = (Gnum) nl * rank;
  vert = malloc ((nl + 1) * sizeof (Gnum));
  edge = malloc ((2 * nl + 2) * sizeof (Gnum));
  if (velo) vlod = malloc ((nl + 1) * sizeof (Gnum));
  if (edlo) elod = malloc ((2 * nl + 2) * sizeof (Gnum));
  if (data) dat  = malloc ((nl + 1) * sizeof (Gnum));
  for (i = 0, ne = 0; i < nl; i ++) {
    Gnum g = lo + i;
    vert[i] = base + ne;
    edge[ne] = base + (g + N - 1) % N; if (edlo) elod[ne] = 1 + ((g + (g + N - 1) % N) % 3); ne ++;
    edge[ne] = base + (g + 1) % N;     if (edlo) elod[ne] = 1 + ((g + (g + 1) % N) % 3); ne ++;
    if (velo) vlod[i] = 1 + (g % 5);
    if (data) dat[i]  = g + 1000;
  }
  vert[nl] = base + ne;

  SCOTCH_dgraphInit (&sg, MPI_COMM_WORLD);
  if (SCOTCH_dgraphBuild (&sg, base, nl, nl, vert, NULL, vlod, NULL, ne, ne, edge, NULL, elod) != 0) {
    fprintf (stderr, "rank %d: build failed\n", rank);
    return (2);
  }
  if (SCOTCH_dgraphCheck (&sg) != 0) {
    fprintf (stderr, "rank %d: source check failed\n", rank);
    return (2);
  }
  g = (Dgraph *) &sg;
  memset (&fg, 0x5a, sizeof (fg));                /* Garbage: folded graph is initialized by the fold itself */

  armed = dlsym (RTLD_DEFAULT, "fi_armed");
  seen  = dlsym (RTLD_DEFAULT, "fi_seen");
  if (armed != NULL) *armed = 1;
  o = dgraphFold (g, partval, &fg, (data ? dat : NULL), (void **) &flddat, GNUM_MPI);
  if (armed != NULL) *armed = 0;
  fprintf (stderr, "rank %d: fold rc=%d seen=%ld\n", rank, o, (seen != NULL) ? *seen : -1L);

  if (o == 0) {
    int                 fldprocnbr = (np + 1) / 2;
    int                 isrecv = (partval == 0) ? (rank < fldprocnbr) : (rank >= fldprocnbr);

    if (isrecv) {
      int                 c = dgraphCheck (&fg);
      int                 bad = 0;
      if (data) {
        Gnum              v;
        for (v = 0; v < fg.vertlocnbr; v ++)
          if (flddat[v] != fg.vnumloctax[v + fg.baseval] - fg.baseval + 1000)
            bad ++;
      }
      fprintf (stderr, "rank %d: folded check=%d vertlocnbr=%ld edgelocnbr=%ld baseval=%ld baddata=%d\n",
               rank, c, (long) fg.vertlocnbr, (long) fg.edgelocnbr, (long) fg.baseval, bad);
      dgraphExit (&fg);
      if (flddat != NULL) free (flddat);
    }
  }
  SCOTCH_dgraphExit (&sg);
  free (vert); free (edge); free (vlod); free (elod); free (dat);
  MPI_Finalize ();
  return (o != 0);
}
