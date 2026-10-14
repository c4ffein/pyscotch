/* CLI-15 reproducer (distributed twin): ParMETIS_V3_Mesh2Dual() under malloc fault injection.
** Each process owns 2 quads of a 2 x (2*npes) quad mesh.  FAILMALLOC_AT=N fails the N-th
** allocation on every process (LD_PRELOAD failmalloc.so, exported through mpirun -x). */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"
#include "parmetis.h"

int
main (int argc, char * argv[])
{
  int                 npes, me, o;
  SCOTCH_Num          baseval = 0, ncommon = 2;
  SCOTCH_Num *        elmdist;
  SCOTCH_Num          eptr[3], eind[8];
  SCOTCH_Num *        xadj   = (SCOTCH_Num *) 0x1;
  SCOTCH_Num *        adjncy = (SCOTCH_Num *) 0x1;
  MPI_Comm            comm = MPI_COMM_WORLD;
  int                 p, k;

  MPI_Init (&argc, &argv);
  MPI_Comm_size (comm, &npes);
  MPI_Comm_rank (comm, &me);
  elmdist = malloc ((npes + 1) * sizeof (SCOTCH_Num));
  for (p = 0; p <= npes; p ++)
    elmdist[p] = 2 * p;
  for (k = 0; k < 2; k ++) {                      /* Quad number q = 2*me+k occupies columns q, q+1 of a 2-row node grid */
    SCOTCH_Num q = 2 * me + k;
    SCOTCH_Num w = 2 * npes + 1;                  /* Nodes per row */
    eptr[k] = 4 * k;
    eind[4 * k] = q; eind[4 * k + 1] = q + 1; eind[4 * k + 2] = w + q + 1; eind[4 * k + 3] = w + q;
  }
  eptr[2] = 8;
  o = ParMETIS_V3_Mesh2Dual (elmdist, eptr, eind, &baseval, &ncommon, &xadj, &adjncy, &comm);
  printf ("rank %d: ParMETIS_V3_Mesh2Dual returned %d (METIS_OK=%d); xadj=%p adjncy=%p\n", me, o, METIS_OK, (void *) xadj, (void *) adjncy);
  if (o == METIS_OK) {
    printf ("rank %d: xadj = %ld %ld %ld\n", me, (long) xadj[0], (long) xadj[1], (long) xadj[2]);
    free (xadj); free (adjncy);
  }
  MPI_Finalize ();
  return (0);
}
