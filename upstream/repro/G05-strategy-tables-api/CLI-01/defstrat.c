#include <stdio.h>
#include <mpi.h>
#include "ptscotch.h"
int main (int argc, char ** argv) {
  SCOTCH_Strat s; MPI_Init (&argc, &argv);
  SCOTCH_stratInit (&s);
  SCOTCH_stratDgraphMapBuild (&s, 0, 3, 9, 0.05);
  SCOTCH_stratSave (&s, stdout); printf ("\n");
  SCOTCH_stratExit (&s); MPI_Finalize (); return 0;
}
