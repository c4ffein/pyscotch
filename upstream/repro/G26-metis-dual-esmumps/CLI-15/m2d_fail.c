/* CLI-15 reproducer: METIS_MeshToDual() under malloc fault injection (LD_PRELOAD failmalloc.so,
** FAILMALLOC_AT=N).  Mesh and checks are those of src/check/test_libmetis_dual.c: the caller
** detects failure by "xadj == NULL", as the Fortran interface has no return value. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
#include "metis.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Num          ne = 6, nn = 7, ncommon = 1, baseval = 0;
  SCOTCH_Num          eptr[] = { 0, 3, 6, 9, 12, 15, 18 };
  SCOTCH_Num          eind[] = { 0, 1, 2, 0, 1, 5, 1, 5, 4, 1, 4, 6, 1, 6, 3, 1, 3, 2 };
  SCOTCH_Num *        xadj   = (SCOTCH_Num *) 0x1;  /* Garbage on purpose */
  SCOTCH_Num *        adjncy = (SCOTCH_Num *) 0x1;
  int                 o;

  o = METIS_MeshToDual (&ne, &nn, eptr, eind, &ncommon, &baseval, &xadj, &adjncy);
  printf ("METIS_MeshToDual returned %d (METIS_OK=%d, METIS_ERROR_MEMORY=%d); xadj=%p adjncy=%p\n",
          o, METIS_OK, METIS_ERROR_MEMORY, (void *) xadj, (void *) adjncy);
  if (xadj == NULL) {                             /* What test_libmetis_dual.c does */
    printf ("caller: error detected through xadj == NULL\n");
    return (1);
  }
  printf ("caller: no error detected, using and freeing xadj/adjncy as the test program does\n");
  printf ("xadj[0] = %ld\n", (long) xadj[0]);
  free (xadj);
  free (adjncy);
  return (0);
}
