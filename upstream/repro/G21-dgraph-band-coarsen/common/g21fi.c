/* Driver for the band / grow / coarsen routines with fault injection (see fishim.c).
** usage: mpirun -np P ./g21fi MODE TOPO BASE NL [ARGS]
**   MODE : band     SCOTCH_dgraphBand (frontier = first local vertex, distance ARGS[0] (default 2))
**          grow     SCOTCH_dgraphGrow (seeds = first and last local vertices, colors 2*rank, 2*rank+1, distance ARGS[0])
**          bandint  internal dgraphBand() (frontier = first local vertex, distance ARGS[0])
**          coarsen  SCOTCH_dgraphCoarsen (flag ARGS[0]: 0 none, 1 fold, 3 folddup; coarnbr ARGS[1] (default 2);
**                   coarrat ARGS[2] (default 0.8); ARGS[3] = 1: pass a user multinode array)
**   TOPO : path   (one path through all vertices of all processes)
**          ring   (same, closed)
**          sparse (local paths; only processes 0 and 1 connected: point-to-point communication for P >= 4)
**   NL vertices per process (process P-1 gets NL + 1 vertices when ARGS[4] = 1 in coarsen mode, to get an odd count)
** The fault shim is armed around the tested call only. Prints "rank R: MODE rc=X seen=N" on each rank.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "module.h"
#include "common.h"
#include "context.h"
#include "graph.h"
#include "dgraph.h"
#include "ptscotch.h"

int dgraphBand (Dgraph * restrict const, const Gnum, Gnum * restrict const, const GraphPart * restrict const, const Gnum, const Gnum, Gnum, Dgraph * restrict const, Gnum * restrict * const, GraphPart * restrict * const, Gnum * const, Gnum * const, Gnum * const, Context *);

int
main (int argc, char * argv[])
{
  int                 rank, np, base, nl, nloc, i, ne, o, dist;
  long                N, lo;
  const char *        mode;
  const char *        topo;
  SCOTCH_Num *        vert;
  SCOTCH_Num *        edge;
  SCOTCH_Num          vertgstnbr;
  SCOTCH_Dgraph       sg;
  volatile long *     armed;
  long *              seen;
  int                 extra = 0;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  if (argc < 5) {
    fprintf (stderr, "usage: g21fi MODE TOPO BASE NL [ARGS]\n");
    return (3);
  }
  mode = argv[1]; topo = argv[2]; base = atoi (argv[3]); nl = atoi (argv[4]);
  dist = (argc > 5) ? atoi (argv[5]) : 2;
  if ((strcmp (mode, "coarsen") == 0) && (argc > 9) && (atoi (argv[9]) == 1))
    extra = 1;
  nloc = nl + ((rank == np - 1) ? extra : 0);     /* Local number of vertices */
  N = (long) nl * np + extra;
  lo = (long) nl * rank;

  vert = malloc ((nloc + 1) * sizeof (SCOTCH_Num));
  edge = malloc ((2 * nloc + 2) * sizeof (SCOTCH_Num));
  for (i = 0, ne = 0; i < nloc; i ++) {
    long g = lo + i;
    vert[i] = base + ne;
    if (strcmp (topo, "ring") == 0) {
      edge[ne ++] = base + (g + N - 1) % N;
      edge[ne ++] = base + (g + 1) % N;
    }
    else if (strcmp (topo, "path") == 0) {
      if (g > 0)     edge[ne ++] = base + g - 1;
      if (g < N - 1) edge[ne ++] = base + g + 1;
    }
    else {                                        /* sparse: local paths, plus one edge between the last vertex of 0 and the first of 1 */
      if (i > 0)        edge[ne ++] = base + g - 1;
      if (i < nloc - 1) edge[ne ++] = base + g + 1;
      if ((rank == 0) && (i == nloc - 1) && (np > 1)) edge[ne ++] = base + lo + nloc;
      if ((rank == 1) && (i == 0))                    edge[ne ++] = base + lo - 1;
    }
  }
  vert[nloc] = base + ne;

  SCOTCH_dgraphInit (&sg, MPI_COMM_WORLD);
  if (SCOTCH_dgraphBuild (&sg, base, nloc, nloc, vert, NULL, NULL, NULL, ne, ne, edge, NULL, NULL) != 0) {
    fprintf (stderr, "rank %d: cannot build graph\n", rank);
    return (2);
  }
  if (SCOTCH_dgraphGhst (&sg) != 0) {
    fprintf (stderr, "rank %d: cannot compute ghost edge array\n", rank);
    return (2);
  }
  SCOTCH_dgraphData (&sg, NULL, NULL, NULL, NULL, &vertgstnbr, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);

  armed = dlsym (RTLD_DEFAULT, "fi_armed");
  seen  = dlsym (RTLD_DEFAULT, "fi_seen");
  o = -99;

  if (strcmp (mode, "band") == 0) {
    SCOTCH_Dgraph       bg;
    SCOTCH_Num *        fron;

    fron = malloc ((nloc + 2) * sizeof (SCOTCH_Num)); /* Frontier array is re-used as queue: must hold all local vertices */
    fron[0] = base;                               /* First local vertex, based */
    SCOTCH_dgraphInit (&bg, MPI_COMM_WORLD);
    if (armed != NULL) *armed = 1;
    o = SCOTCH_dgraphBand (&sg, 1, fron, dist, &bg);
    if (armed != NULL) *armed = 0;
    if (o == 0) {
      fprintf (stderr, "rank %d: band check=%d\n", rank, SCOTCH_dgraphCheck (&bg));
      SCOTCH_dgraphExit (&bg);
    }
    free (fron);
  }
  else if (strcmp (mode, "grow") == 0) {
    SCOTCH_Num *        seed;
    SCOTCH_Num *        part;

    seed = malloc ((nloc + 2) * sizeof (SCOTCH_Num)); /* Seed array is re-used as queue: must hold all local vertices */
    part = malloc ((vertgstnbr + 1) * sizeof (SCOTCH_Num));
    memset (part, ~0, (vertgstnbr + 1) * sizeof (SCOTCH_Num));
    seed[0] = base;
    seed[1] = base + nloc - 1;
    part[0] = 2 * rank;
    part[nloc - 1] = 2 * rank + 1;
    if (armed != NULL) *armed = 1;
    o = SCOTCH_dgraphGrow (&sg, (nloc > 1) ? 2 : 1, seed, dist, part);
    if (armed != NULL) *armed = 0;
    if (o == 0) {
      int                 bad = 0;
      for (i = 0; i < nloc; i ++)
        if ((part[i] < -1) || (part[i] >= 2 * np)) bad ++;
      fprintf (stderr, "rank %d: grow bad=%d part[0..3]=%ld,%ld,%ld,%ld\n", rank, bad, (long) part[0], (long) part[1 % nloc], (long) part[2 % nloc], (long) part[3 % nloc]);
    }
    free (part);                                  /* Double free if the library freed the user array */
    free (seed);
  }
  else if (strcmp (mode, "bandint") == 0) {
    Dgraph              bg;
    Dgraph *            g = (Dgraph *) &sg;
    GraphPart *         part;
    Gnum *              fron;
    Gnum *              bfron;
    GraphPart *         bpart;
    Gnum                lvl, v1, anc;
    Context             cd;

    contextInit (&cd); contextOptionsInit (&cd); contextCommit (&cd);
    part = malloc (vertgstnbr + 8);
    memset (part, 0, vertgstnbr + 8);
    part[0] = 2;                                  /* Frontier vertex is in part 2 */
    fron = malloc ((nloc + 2) * sizeof (Gnum));   /* Frontier array is re-used as queue: must hold all local vertices */
    fron[0] = base;
    dgraphInit (&bg, MPI_COMM_WORLD);
    if (armed != NULL) *armed = 1;
    o = dgraphBand (g, 1, fron, part - base, nloc, 0, dist, &bg, &bfron, &bpart, &lvl, &v1, &anc, &cd);
    if (armed != NULL) *armed = 0;
    if (o == 0) {
      fprintf (stderr, "rank %d: bandint check=%d vertlocnbr=%ld\n", rank, dgraphCheck (&bg), (long) bg.vertlocnbr);
      memFree (bpart + base);
      memFree (bfron);
      dgraphExit (&bg);
    }
    contextExit (&cd);
    free (part); free (fron);
  }
  else if (strcmp (mode, "coarsen") == 0) {
    SCOTCH_Dgraph       cg;
    SCOTCH_Num *        mult = NULL;
    int                 flag    = (argc > 5) ? atoi (argv[5]) : 0;
    SCOTCH_Num          coarnbr = (argc > 6) ? atoi (argv[6]) : 2;
    double              coarrat = (argc > 7) ? atof (argv[7]) : 0.8;
    int                 usemult = (argc > 8) ? atoi (argv[8]) : 1;
    SCOTCH_Num          flagval = (flag == 1) ? SCOTCH_COARSENFOLD : ((flag == 3) ? SCOTCH_COARSENFOLDDUP : SCOTCH_COARSENNONE);

    SCOTCH_dgraphInit (&cg, MPI_COMM_WORLD);
    if (usemult) {
      SCOTCH_Num          cmax = SCOTCH_dgraphCoarsenVertLocMax (&sg, flagval);
      mult = malloc ((2 * cmax + 8) * sizeof (SCOTCH_Num));
      memset (mult, 0x55, (2 * cmax + 8) * sizeof (SCOTCH_Num));
    }
    if (armed != NULL) *armed = 1;
    o = SCOTCH_dgraphCoarsen (&sg, coarnbr, coarrat, flagval, &cg, mult);
    if (armed != NULL) *armed = 0;
    if (o == 0) {
      SCOTCH_Num          cvl, cvg;
      int                 cpn;
      SCOTCH_dgraphData (&cg, NULL, &cvg, &cvl, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
      cpn = ((Dgraph *) &cg)->procglbnbr;
      fprintf (stderr, "rank %d: coarsen vertglbnbr=%ld vertlocnbr=%ld check=%d\n", rank, (long) cvg, (long) cvl, (cpn > 0) ? SCOTCH_dgraphCheck (&cg) : -1);
      if (cpn > 0)
        SCOTCH_dgraphExit (&cg);
    }
    free (mult);
  }
  else {
    fprintf (stderr, "unknown mode\n");
    return (3);
  }

  fprintf (stderr, "rank %d: %s rc=%d seen=%ld\n", rank, mode, o, (seen != NULL) ? *seen : -1L);
  SCOTCH_dgraphExit (&sg);
  free (vert); free (edge);
  MPI_Finalize ();
  return ((o != 0) ? 1 : 0);
}
