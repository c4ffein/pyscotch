/* mchk base : single process, path graph of 3 vertices; vertices b and b+1 are mated in one multinode, the last vertex b+2 is
   left unmatched (mategsttax = -1, no multinode). dgraphMatchCheck() must return 1 whatever the base value. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "module.h"
#include "common.h"
#include "graph.h"
#include "dgraph.h"
#include "dgraph_coarsen.h"
#include "dgraph_match.h"
#include "ptscotch.h"
int main (int argc, char ** argv) {
  int b = atoi (argv[1]), rc, nsnd[1] = { 0 };
  SCOTCH_Num vert[4], edge[4];
  SCOTCH_Dgraph sg; Dgraph * g; DgraphMatchData m; DgraphCoarsenMulti mult[1]; Gnum * mate, * mt, vsd[2] = { 0, 0 };
  MPI_Init (&argc, &argv);
  vert[0] = b; vert[1] = b + 1; vert[2] = b + 3; vert[3] = b + 4;
  edge[0] = b + 1; edge[1] = b; edge[2] = b + 2; edge[3] = b + 1;
  SCOTCH_dgraphInit (&sg, MPI_COMM_WORLD);
  if (SCOTCH_dgraphBuild (&sg, b, 3, 3, vert, NULL, NULL, NULL, 4, 4, edge, NULL, NULL) != 0 || SCOTCH_dgraphGhst (&sg) != 0) return (2);
  g = (Dgraph *) &sg;
  mate = malloc ((g->vertgstnbr + 1) * sizeof (Gnum)); mt = mate - b;
  mt[b] = b + 1; mt[b + 1] = b; mt[b + 2] = -1;                   /* Last local vertex unmatched */
  memset (mult, 0, sizeof (mult)); mult[0].vertglbnum[0] = b; mult[0].vertglbnum[1] = b + 1;
  memset (&m, 0, sizeof (m));
  m.c.finegrafptr = g; m.mategsttax = mt; m.c.multlocnbr = 1; m.c.multloctab = mult; m.c.nsndidxtab = nsnd; m.c.vsnddsptab = (int *) vsd;
  rc = dgraphMatchCheck (&m);
  printf ("base=%d dgraphMatchCheck rc=%d (expected 1: vertex %d is unmatched)\n", b, rc, b + 2);
  MPI_Finalize (); return (rc == 0);
}
