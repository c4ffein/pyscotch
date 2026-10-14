/* DGR-04 reproducer: SCOTCH_dgraphRedist() with a user-provided permutation
** that reverses the vertex order inside each part.
** usage: mpirun -np P ./redistperm N base mode
**   N    : number of vertices of a ring graph, block-distributed
**   base : base value
**   mode : 0 = all vertices to the last process (the review's example),
**          1 = packs of 3 vertices to successive processes (as in test_scotch_dgraph_redist.c)
**          2 = all vertices held by process 0, all sent to the (empty) last process
** Each run is done twice: with the identity-in-part permutation (control)
** and with the reversed permutation. The redistributed graph is checked
** with SCOTCH_dgraphCheck() and its adjacency compared with the ring.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "scotch.h"
#include "ptscotch.h"

static int
run (int rev, SCOTCH_Num N, SCOTCH_Num base, int mode, int rank, int np)
{
  SCOTCH_Num          lo = N * rank / np, hi = N * (rank + 1) / np, nl;
  SCOTCH_Num *        vert;
  SCOTCH_Num *        edge;
  SCOTCH_Num *        part;
  SCOTCH_Num *        perm;
  SCOTCH_Num *        cntloctab = calloc (np, sizeof (SCOTCH_Num)); /* Vertices of each part held locally       */
  SCOTCH_Num *        cntglbtab = calloc (np, sizeof (SCOTCH_Num)); /* Vertices of each part globally          */
  SCOTCH_Num *        cntscntab = calloc (np, sizeof (SCOTCH_Num)); /* Vertices of each part on ranks <= mine  */
  SCOTCH_Num *        dsptab    = calloc (np + 1, sizeof (SCOTCH_Num));
  SCOTCH_Num          i, vgn, bv, rc, ck, bad;
  SCOTCH_Num *        egt;
  SCOTCH_Num *        elt;
  SCOTCH_Dgraph       g, r;
  int                 p;

  if (mode == 2) {                                /* All vertices on process 0, all sent to the last process, which is empty */
    lo = (rank == 0) ? 0 : N;
    hi = N;
  }
  nl = hi - lo;
  vert = malloc ((nl + 1) * sizeof (SCOTCH_Num));
  edge = malloc ((2 * nl + 2) * sizeof (SCOTCH_Num));
  part = malloc ((nl + 1) * sizeof (SCOTCH_Num));
  for (i = 0; i < nl; i ++) {
    SCOTCH_Num g = lo + i;
    vert[i] = base + 2 * i;
    edge[2 * i]     = base + (g + N - 1) % N;
    edge[2 * i + 1] = base + (g + 1) % N;
    part[i] = (mode != 1) ? (np - 1) : ((g / 3) % np);
    cntloctab[part[i]] ++;
  }
  vert[nl] = base + 2 * nl;

  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  if (SCOTCH_dgraphBuild (&g, base, nl, nl, vert, NULL, NULL, NULL, 2 * nl, 2 * nl, edge, NULL, NULL) != 0) { fprintf (stderr, "build failed\n"); return (2); }
  if (SCOTCH_dgraphCheck (&g) != 0) { fprintf (stderr, "source check failed\n"); return (2); }
  if (SCOTCH_dgraphGhst (&g) != 0) return (2);
  SCOTCH_dgraphData (&g, &bv, NULL, NULL, NULL, &vgn, NULL, NULL, NULL, NULL, NULL, NULL, NULL, &elt, &egt, NULL, NULL);

  MPI_Allreduce (cntloctab, cntglbtab, np, (sizeof (SCOTCH_Num) == 8) ? MPI_LONG : MPI_INT, MPI_SUM, MPI_COMM_WORLD);
  MPI_Scan      (cntloctab, cntscntab, np, (sizeof (SCOTCH_Num) == 8) ? MPI_LONG : MPI_INT, MPI_SUM, MPI_COMM_WORLD);
  for (p = 0, dsptab[0] = base; p < np; p ++) {   /* Start index of each part in the redistributed numbering */
    dsptab[p + 1] = dsptab[p] + cntglbtab[p];
    cntscntab[p] -= cntloctab[p];                 /* Number of vertices of part p on ranks < mine */
  }
  perm = malloc (vgn * sizeof (SCOTCH_Num));      /* Permutation array sized on local + ghost vertices */
  for (i = 0; i < nl; i ++) {                     /* Rank of local vertex within its part, in global index order */
    SCOTCH_Num          idx = cntscntab[part[i]] ++;
    perm[i] = dsptab[part[i]] + (rev ? (cntglbtab[part[i]] - 1 - idx) : idx);
  }
  if (SCOTCH_dgraphHalo (&g, perm, (sizeof (SCOTCH_Num) == 8) ? MPI_LONG : MPI_INT) != 0) return (2); /* Fill ghost part */

  SCOTCH_dgraphInit (&r, MPI_COMM_WORLD);
  rc = SCOTCH_dgraphRedist (&g, part, perm, 0, 0, &r);
  ck = bad = -1;
  if (rc == 0) {
    SCOTCH_Num          rnl, rbv, *rvt, *rve, *rvl, *rel, v;
    ck = SCOTCH_dgraphCheck (&r);
    SCOTCH_dgraphData (&r, &rbv, NULL, &rnl, NULL, NULL, &rvt, &rve, NULL, &rvl, NULL, NULL, NULL, &rel, NULL, NULL, NULL);
    for (v = 0, bad = 0; v < rnl; v ++) {         /* Vertex label is the original global index; neighbours must be its ring neighbours */
      SCOTCH_Num          lab = rvl[v] - base, n1 = (lab + N - 1) % N, n2 = (lab + 1) % N, a, b, p1, p2;
      SCOTCH_Num          q1, q2, i1, i2;
      /* Expected new numbers of n1 and n2: part of n, then rank within part */
      q1 = (mode != 1) ? (np - 1) : ((n1 / 3) % np); q2 = (mode != 1) ? (np - 1) : ((n2 / 3) % np);
      i1 = 0; i2 = 0;
      { SCOTCH_Num x; for (x = 0; x < n1; x ++) if (((mode != 1) ? (np - 1) : ((x / 3) % np)) == q1) i1 ++;
                      for (x = 0; x < n2; x ++) if (((mode != 1) ? (np - 1) : ((x / 3) % np)) == q2) i2 ++; }
      p1 = dsptab[q1] + (rev ? (cntglbtab[q1] - 1 - i1) : i1);
      p2 = dsptab[q2] + (rev ? (cntglbtab[q2] - 1 - i2) : i2);
      if ((rve[v] - rvt[v]) != 2) { bad ++; continue; }
      a = rel[rvt[v] - rbv]; b = rel[rvt[v] - rbv + 1];
      if (! ((a == p1 && b == p2) || (a == p2 && b == p1))) bad ++;
    }
    SCOTCH_dgraphExit (&r);
  }
  fprintf (stderr, "rank %d: rev=%d rc=%ld check=%ld bad-adjacency=%ld\n", rank, rev, (long) rc, (long) ck, (long) bad);
  SCOTCH_dgraphExit (&g);
  free (vert); free (edge); free (part); free (perm); free (cntloctab); free (cntglbtab); free (cntscntab); free (dsptab);
  return ((rc != 0) || (ck != 0) || (bad != 0));
}

int
main (int argc, char * argv[])
{
  int                 rank, np, o;
  SCOTCH_Num          N, base;
  int                 mode;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &rank);
  MPI_Comm_size (MPI_COMM_WORLD, &np);
  N = atol (argv[1]); base = atol (argv[2]); mode = atoi (argv[3]);
  o  = run (0, N, base, mode, rank, np);          /* Control: identity order within parts */
  o |= run (1, N, base, mode, rank, np) << 1;     /* Reversed order within parts            */
  MPI_Finalize ();
  return (o);
}
