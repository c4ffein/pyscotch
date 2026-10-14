/* CLI-07 (ParMETIS half): ncon = 2, strided tpwgts and ubvec in ParMETIS_V3_PartKway. */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
#include "parmetis.h"
#include "../common/grid.h"
int main (int argc, char * argv[])
{
  setvbuf (stdout, NULL, _IONBF, 0);
  int rank, size, w = 40, h = 40, v, p, r;
  SCOTCH_Num n = w * h, ncon = 2, nparts = 4, wgtflag = 2, numflag = 0, edgecut = -1;
  SCOTCH_Num * xadj, * adjncy, * part, * vwgt, vtxdist[2];
  float tpwgts[8] = { 0.10f, 0.5f, 0.20f, 0.5f, 0.30f, 0.0f, 0.40f, 0.0f };
  float ub[2] = { 1.03f, 1.03f };
  MPI_Comm comm = MPI_COMM_WORLD;
  MPI_Init (&argc, &argv);
  MPI_Comm_rank (comm, &rank); MPI_Comm_size (comm, &size);
  if (size != 1) { if (rank == 0) fprintf (stderr, "run with -np 1 (single-process distributed graph is enough)\n"); MPI_Finalize (); return 2; }
  gridBuild (w, h, 0, &xadj, &adjncy);
  vwgt = malloc (n * ncon * sizeof (SCOTCH_Num)); part = malloc (n * sizeof (SCOTCH_Num));
  srand (1);
  for (v = 0; v < n; v ++) { vwgt[v * 2] = 1 + rand () % 10; vwgt[v * 2 + 1] = 1000 + v; }
  vtxdist[0] = 0; vtxdist[1] = n;
  r = ParMETIS_V3_PartKway (vtxdist, xadj, adjncy, vwgt, NULL, &wgtflag, &numflag, &ncon, &nparts, tpwgts, ub, NULL, &edgecut, part, &comm);
  printf ("ret=%d edgecut=%ld\n", r, (long) edgecut);
  if (r == METIS_OK) {
    for (p = 0; p < nparts; p ++) {
      double l0 = 0, t0 = 0, lx = 0, tx = 0;
      for (v = 0; v < n; v ++) { t0 += vwgt[2 * v]; tx += vwgt[v]; if (part[v] == p) { l0 += vwgt[2 * v]; lx += vwgt[v]; } }
      printf ("part %d: target0=%.2f (tpwgts as read, unstrided: %.2f) constraint0=%.4f as-read(vwgt[v])=%.4f\n", p, tpwgts[2 * p], tpwgts[p], l0 / t0, lx / tx);
    }
  }
  MPI_Finalize ();
  return (r == METIS_OK) ? 0 : 1;
}
