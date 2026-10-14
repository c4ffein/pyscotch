/* API-19: SCOTCH_dgraphStat edlosum convention, distributed twin of stat.c.
** Same 4-vertex path, distributed over the processes; expected 3, 3, 10.
** Run with 1 and 2 processes.
*/

#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"

static SCOTCH_Num
dstat (const int procnum, const int procnbr, const int wgtflag, double * const avgptr)
{
  SCOTCH_Dgraph grafdat;
  SCOTCH_Num    verttab[5];
  SCOTCH_Num    edgetab[6];
  SCOTCH_Num    edlotab[6];
  SCOTCH_Num    vertlocnbr, vertlocbas, edgelocnbr;
  SCOTCH_Num    vertnum, vertlocnum, edgelocnum;
  SCOTCH_Num    velomin, velomax, velosum, degrmin, degrmax, edlomin, edlomax, edlosum;
  double        veloavg, velodlt, degravg, degrdlt, edloavg, edlodlt;
  const SCOTCH_Num edloedge[3] = { 2, 5, 3 };     /* Loads of edges (0,1), (1,2), (2,3) */

  vertlocbas = (4 * procnum) / procnbr;           /* Block distribution of the 4 vertices */
  vertlocnbr = (4 * (procnum + 1)) / procnbr - vertlocbas;
  for (vertlocnum = 0, edgelocnum = 0; vertlocnum < vertlocnbr; vertlocnum ++) {
    vertnum = vertlocbas + vertlocnum;
    verttab[vertlocnum] = edgelocnum;
    if (vertnum > 0) {
      edgetab[edgelocnum] = vertnum - 1;
      edlotab[edgelocnum ++] = (wgtflag == 2) ? edloedge[vertnum - 1] : 1;
    }
    if (vertnum < 3) {
      edgetab[edgelocnum] = vertnum + 1;
      edlotab[edgelocnum ++] = (wgtflag == 2) ? edloedge[vertnum] : 1;
    }
  }
  verttab[vertlocnbr] = edgelocnum;
  edgelocnbr = edgelocnum;

  SCOTCH_dgraphInit (&grafdat, MPI_COMM_WORLD);
  if ((SCOTCH_dgraphBuild (&grafdat, 0, vertlocnbr, vertlocnbr, verttab, NULL, NULL, NULL,
                           edgelocnbr, edgelocnbr, edgetab, NULL, (wgtflag != 0) ? edlotab : NULL) != 0) ||
      (SCOTCH_dgraphCheck (&grafdat) != 0)) {
    fprintf (stderr, "cannot build dgraph\n");
    MPI_Abort (MPI_COMM_WORLD, 1);
  }
  if (SCOTCH_dgraphStat (&grafdat, &velomin, &velomax, &velosum, &veloavg, &velodlt,
                         &degrmin, &degrmax, &degravg, &degrdlt,
                         &edlomin, &edlomax, &edlosum, &edloavg, &edlodlt) != 0) {
    fprintf (stderr, "dgraphStat failed\n");
    MPI_Abort (MPI_COMM_WORLD, 1);
  }
  SCOTCH_dgraphExit (&grafdat);
  *avgptr = edloavg;
  return (edlosum);
}

int
main (int argc, char * argv[])
{
  int        procnum, procnbr;
  SCOTCH_Num suma, sumb, sumc;
  double     avga, avgb, avgc;
  int        o;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &procnum);
  MPI_Comm_size (MPI_COMM_WORLD, &procnbr);

  suma = dstat (procnum, procnbr, 0, &avga);
  sumb = dstat (procnum, procnbr, 1, &avgb);
  sumc = dstat (procnum, procnbr, 2, &avgc);
  o = ((suma != 3) || (sumb != 3) || (sumc != 10) || (avga != 1.0) || (avgb != 1.0) || (avgc != 10.0 / 3.0));
  if (procnum == 0) {
    printf ("%d procs, no loads:   edlosum=%ld avg=%g (expected 3, 1)\n", procnbr, (long) suma, avga);
    printf ("%d procs, unit loads: edlosum=%ld avg=%g (expected 3, 1)\n", procnbr, (long) sumb, avgb);
    printf ("%d procs, loads 2,5,3: edlosum=%ld avg=%g (expected 10, 3.33333)\n", procnbr, (long) sumc, avgc);
    printf ("%s\n", o ? "FAIL" : "ok");
  }
  MPI_Finalize ();
  return (o ? EXIT_FAILURE : EXIT_SUCCESS);
}
