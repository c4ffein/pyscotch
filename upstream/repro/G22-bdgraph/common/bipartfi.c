/* Driver for the distributed bipartitioning methods (bdgraphBipartSt) with fault injection (see fishim.c).
** usage: mpirun -np P ./bipartfi graphfile baseval "strategy" [veex] [check]
**   graphfile : centralized Scotch graph file, loaded as a distributed graph
**   baseval   : base value for the loaded graph
**   strategy  : bdgraph bipartitioning strategy string (bdgraphbipartststratab)
**   veex      : 1 to attach a pseudo-random external gain array (veexloctax) to the active graph
**   check     : 1 to run bdgraphCheck() after the strategy when all processes returned 0
** All processes print their return value and the global partition data of the active graph,
** plus the 'bal' strategy variable (bbalglbval) and its value recomputed from compglbload0dlt.
** Fault injection: the shim is armed around bdgraphBipartSt() only.
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
#include "parser.h"
#include "arch.h"
#include "graph.h"
#include "bgraph.h"
#include "dgraph.h"
#include "dmapping.h"
#include "bdgraph.h"
#include "bdgraph_bipart_st.h"
#include "scotch.h"
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  int                 rank, np;
  int                 base, veexflag, chekflag;
  FILE *              stream;
  SCOTCH_Dgraph       sg;
  SCOTCH_Arch         sa;
  Dgraph *            g;
  Arch *              a;
  ArchDom             domnorg;
  ArchDom             domnsub[2];
  Bdgraph             bg;
  Context             contdat;
  Strat *             straptr;
  volatile long *     armed;
  int                 o, oglb;
  double              balcalc;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  if (argc < 4) {
    if (rank == 0) fprintf (stderr, "usage: bipartfi graphfile baseval strategy [veex] [check]\n");
    MPI_Finalize ();
    return (2);
  }
  base     = atoi (argv[2]);
  veexflag = (argc > 4) ? atoi (argv[4]) : 0;
  chekflag = (argc > 5) ? atoi (argv[5]) : 0;

  SCOTCH_randomProc (rank);                       /* Distinct pseudo-random seeds, as in dgmap */
  SCOTCH_randomReset ();

  SCOTCH_dgraphInit (&sg, MPI_COMM_WORLD);
  stream = NULL;                                  /* Centralized file: only the root process reads it */
  if ((rank == 0) && ((stream = fopen (argv[1], "r")) == NULL)) {
    fprintf (stderr, "rank %d: cannot open graph file\n", rank);
    return (2);
  }
  if (SCOTCH_dgraphLoad (&sg, stream, base, 0) != 0) {
    fprintf (stderr, "rank %d: cannot load graph\n", rank);
    return (2);
  }
  if (stream != NULL)
    fclose (stream);
  g = (Dgraph *) &sg;
  if (dgraphGhst (g) != 0) {
    fprintf (stderr, "rank %d: cannot compute ghost edge array\n", rank);
    return (2);
  }

  contextInit (&contdat);
  contextOptionsInit (&contdat);
  if (contextCommit (&contdat) != 0) {
    fprintf (stderr, "rank %d: cannot commit context\n", rank);
    return (2);
  }

  SCOTCH_archInit (&sa);
  SCOTCH_archCmplt (&sa, 2);
  a = (Arch *) &sa;
  archDomFrst (a, &domnorg);
  if (archDomBipart (a, &domnorg, &domnsub[0], &domnsub[1]) != 0) {
    fprintf (stderr, "rank %d: cannot bipartition domain\n", rank);
    return (2);
  }

  memset (&bg, 0x5a, sizeof (bg));                /* Garbage: active graph is initialized by bdgraphInit */
  if (bdgraphInit (&bg, g, NULL, a, domnsub) != 0) {
    fprintf (stderr, "rank %d: cannot initialize active graph\n", rank);
    return (2);
  }
  bg.levlnum = 0;
  bg.contptr = &contdat;

  if (veexflag != 0) {                            /* Attach external gains: all vertices are in part 0 */
    Gnum                vertlocnum;
    Gnum                vertglbadj;
    Gnum                veexlocsum;
    Gnum                veexglbsum;
    Gnum *              veexloctab;

    if ((veexloctab = memAlloc (bg.s.vertlocnbr * sizeof (Gnum))) == NULL) {
      fprintf (stderr, "rank %d: out of memory\n", rank);
      return (2);
    }
    vertglbadj = bg.s.procvrttab[bg.s.proclocnum] - bg.s.baseval;
    for (vertlocnum = 0, veexlocsum = 0; vertlocnum < bg.s.vertlocnbr; vertlocnum ++) {
      Gnum                vertglbnum = vertlocnum + bg.s.baseval + vertglbadj;
      veexloctab[vertlocnum] = ((vertglbnum * 7919) % 11) - 5; /* Deterministic, both signs */
      veexlocsum += veexloctab[vertlocnum];
    }
    MPI_Allreduce (&veexlocsum, &veexglbsum, 1, GNUM_MPI, MPI_SUM, MPI_COMM_WORLD);
    bg.veexloctax       = veexloctab - bg.s.baseval;
    bg.veexglbsum       = veexglbsum;
    bg.commglbloadextn0 = 0;                      /* External load when all vertices are in part 0 */
    bg.commglbgainextn0 =                         /* External gain if all swapped to part 1        */
    bg.commglbgainextn  = veexglbsum;
    bg.commglbload      = bg.commglbloadextn0;
    if (bdgraphCheck (&bg) != 0) {
      fprintf (stderr, "rank %d: initial active graph with external gains is inconsistent\n", rank);
      return (2);
    }
  }

  if (strcmp (argv[3], "gather") == 0) {          /* Special mode: check bdgraphGatherAll() on the current active graph */
    Bgraph              cg;
    Gnum                vertnum;
    Gnum                badnbr;
    Gnum *              vnumloctax;

    vnumloctax = bg.s.vnumloctax;                 /* As bdgraphBipartSq() does */
    bg.s.vnumloctax = NULL;
    o = bdgraphGatherAll (&bg, &cg);
    bg.s.vnumloctax = vnumloctax;
    printf ("rank %d: gather ret=%d\n", rank, o);
    if (o == 0) {
      for (vertnum = cg.s.baseval, badnbr = 0; vertnum < cg.s.vertnnd; vertnum ++) {
        if ((cg.veextax != NULL) && (cg.veextax[vertnum] != (((vertnum * 7919) % 11) - 5)))
          badnbr ++;
      }
      printf ("rank %d: gather veextax=%p bad=%ld of %ld, bbalval=%.9g, compload0dlt=%ld compload0avg=%ld\n", rank,
              (void *) cg.veextax, (long) badnbr, (long) cg.s.vertnbr, cg.bbalval, (long) cg.compload0dlt, (long) cg.compload0avg);
      bgraphExit (&cg);
    }
    fflush (stdout);
    bdgraphExit (&bg);
    SCOTCH_dgraphExit (&sg);
    SCOTCH_archExit (&sa);
    contextExit (&contdat);
    MPI_Finalize ();
    return (o);
  }

  if ((straptr = stratInit (&bdgraphbipartststratab, argv[3])) == NULL) {
    fprintf (stderr, "rank %d: invalid strategy\n", rank);
    return (2);
  }

  armed = dlsym (RTLD_DEFAULT, "fi_armed");
  if (armed != NULL) *armed = 1;
  o = bdgraphBipartSt (&bg, straptr);
  if (armed != NULL) *armed = 0;

  balcalc = (bg.compglbload0avg != 0) ? ((double) ABS (bg.compglbload0dlt) / (double) bg.compglbload0avg) : 0.0;
  printf ("rank %d: ret=%d load0=%ld dlt=%ld size0=%ld comm=%ld gainextn=%ld fron=%ld bal=%.9g balcalc=%.9g\n",
          rank, o, (long) bg.compglbload0, (long) bg.compglbload0dlt, (long) bg.compglbsize0, (long) bg.commglbload,
          (long) bg.commglbgainextn, (long) bg.fronglbnbr, bg.bbalglbval, balcalc);
  fflush (stdout);

  MPI_Allreduce (&o, &oglb, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD); /* Driver's own agreement: do not call collective check if some rank failed */
  if ((oglb == 0) && (chekflag != 0)) {
    int                 c;

    c = bdgraphCheck (&bg);
    printf ("rank %d: check=%d\n", rank, c);
    fflush (stdout);
    if (c != 0) o = 3;
  }

  stratExit (straptr);
  bdgraphExit (&bg);
  SCOTCH_dgraphExit (&sg);
  SCOTCH_archExit (&sa);
  contextExit (&contdat);
  MPI_Finalize ();
  return (o);
}
