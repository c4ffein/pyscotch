/* chk VARIANT base : 2 vertices per process (vertlocmax 4: a numbering hole of 2 slots per process), SCOTCH_dgraphBuild then SCOTCH_dgraphCheck.
   ok     : bidirectional ring over all vertices, loads 1..5
   far    : one extra arc on vertex 0 of process 0 to global number procvrttab[P] + 7 (outside every process range)
   hole   : one extra arc on vertex 0 of process 0 to the first hole slot of process 1 (or of process 0 when np = 1)
   zero   : ring with all edge loads 0; neg : all edge loads -3 (symmetric, so the matching rounds cannot see it)
   negasym: load of one arc negative only on one side */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char ** argv) {
  int rank, np, rc, ck, ne = 0, i;
  const char * v = argv[1]; int b = atoi (argv[2]);
  SCOTCH_Num vert[3], edge[8], edlo[8], * edl = edlo;
  SCOTCH_Num N, g0, g1, prev, next;
  SCOTCH_Dgraph g;
  MPI_Init (&argc, &argv); MPI_Comm_rank (MPI_COMM_WORLD, &rank); MPI_Comm_size (MPI_COMM_WORLD, &np);
  N = 4 * np; g0 = b + 4 * rank; g1 = g0 + 1;                    /* Global numbers: process r owns b+4r, b+4r+1; slots b+4r+2, b+4r+3 are holes */
  prev = (rank == 0) ? (b + 4 * (np - 1) + 1) : (g0 - 3);        /* Vertex 1 of previous process */
  next = (rank == np - 1) ? b : (g0 + 4);                        /* Vertex 0 of next process      */
  vert[0] = b + ne; edge[ne] = g1; edlo[ne ++] = 2; edge[ne] = prev; edlo[ne ++] = 3;
  if (np == 1) ne --;                                             /* Single process: prev == g1 */
  if (! strcmp (v, "far"))  { edge[ne] = b + N + 7; edlo[ne ++] = 1; }
  if (! strcmp (v, "hole")) { edge[ne] = (np > 1) ? (b + 4 + 2) : (g0 + 2); edlo[ne ++] = 1; }
  vert[1] = b + ne; edge[ne] = g0; edlo[ne ++] = 2; edge[ne] = next; edlo[ne ++] = 3;
  if (np == 1) ne --;
  vert[2] = b + ne;
  if (! strcmp (v, "zero")) for (i = 0; i < ne; i ++) edlo[i] = 0;
  if (! strcmp (v, "neg"))  for (i = 0; i < ne; i ++) edlo[i] = -3;
  if (! strcmp (v, "negasym") && rank == 0) edlo[0] = -3;
  SCOTCH_dgraphInit (&g, MPI_COMM_WORLD);
  rc = SCOTCH_dgraphBuild (&g, b, 2, 4, vert, NULL, NULL, NULL, ne, ne, edge, NULL, edl);
  ck = SCOTCH_dgraphCheck (&g);
  fprintf (stderr, "r%d variant=%s base=%d build rc=%d check rc=%d\n", rank, v, b, rc, ck);
  SCOTCH_dgraphExit (&g);
  MPI_Finalize (); return (ck != 0);
}
