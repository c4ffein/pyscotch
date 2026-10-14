/* API-07: PT-Scotch strategy builders with an absurd imbalance ratio */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Strat  s;
  double        v = (argc > 1) ? atof (argv[1]) : 1e300;
  int           r;

  MPI_Init (&argc, &argv);
  SCOTCH_stratInit (&s); r = SCOTCH_stratDgraphMapBuild     (&s, SCOTCH_STRATDEFAULT, 3, 4, v);    printf ("DgraphMapBuild     (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); r = SCOTCH_stratDgraphClusterBuild (&s, SCOTCH_STRATDEFAULT, 3, 4, v, v); printf ("DgraphClusterBuild (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); r = SCOTCH_stratDgraphOrderBuild   (&s, SCOTCH_STRATDEFAULT, 3, 0, v);    printf ("DgraphOrderBuild   (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  MPI_Finalize ();
  return (0);
}
