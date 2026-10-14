/* lab VARIANT base : 2 vertices per process with labels 100*(r+1)+{1,2}; vertex 0 has arcs to its own vertex 1 and to
   vertex 1 of the previous process, vertex 1 to its own vertex 0 and to vertex 0 of the next process (symmetric ring of
   processes; np = 1: own vertex only). Edge arrays are non-compact:
   every vertex has one gap slot after its arcs (edgelocsiz = edgelocnbr + 2).
   noncompact : valid graph; after the build the real slots must hold global numbers and SCOTCH_dgraphCheck must pass
   unknown    : process 1 (or 0 if np = 1) has an arc to label 9999, found on no process: the build must fail on ALL processes
   dup        : process 1 (or 0) has two vertices with the same label: the build must fail on ALL processes */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char ** argv) {
  int rank, np, rc, ck = -1, bad, ne = 0, i;
  const char * v = argv[1]; int b = atoi (argv[2]);
  SCOTCH_Num vert[2], vend[2], lbl[2], edge[8], nxt, prv;
  SCOTCH_Dgraph g;
  MPI_Init (&argc, &argv); MPI_Comm_rank (MPI_COMM_WORLD, &rank); MPI_Comm_size (MPI_COMM_WORLD, &np);
  bad = (np > 1) ? 1 : 0;
  lbl[0] = 100 * (rank + 1) + 1; lbl[1] = 100 * (rank + 1) + 2;
  if (! strcmp (v, "dup") && rank == bad) lbl[1] = lbl[0];
  nxt = 100 * ((rank + 1) % np + 1); prv = 100 * ((rank + np - 1) % np + 1);
  vert[0] = b + ne; edge[ne ++] = lbl[1]; if (np > 1) { edge[ne ++] = prv + 2; }
  if (! strcmp (v, "unknown") && rank == bad) edge[ne ++] = 9999;
  vend[0] = b + ne; edge[ne ++] = -1;                             /* Gap slot */
  vert[1] = b + ne; edge[ne ++] = lbl[0]; if (np > 1) { edge[ne ++] = nxt + 1; }
  vend[1] = b + ne; edge[ne ++] = -1;                             /* Gap slot */
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  rc = SCOTCH_dgraphBuild (&g, b, 2, 2, vert, vend, NULL, lbl, ne - 2, ne, edge, NULL, NULL);
  if (rc == 0) ck = SCOTCH_dgraphCheck (&g);
  fprintf (stderr, "r%d variant=%s base=%d build rc=%d check rc=%d edges=[", rank, v, b, rc, ck);
  for (i = 0; i < ne; i ++) fprintf (stderr, " %ld", (long) edge[i]);
  fprintf (stderr, " ] (vert=[%ld %ld] vend=[%ld %ld], expected global numbers in real slots, gap slots untouched)\n", (long) vert[0], (long) vert[1], (long) vend[0], (long) vend[1]);
  SCOTCH_dgraphExit (&g);
  MPI_Finalize (); return (0);
}
