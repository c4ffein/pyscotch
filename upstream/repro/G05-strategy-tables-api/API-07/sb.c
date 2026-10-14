/* API-07: sequential strategy builders with an absurd imbalance ratio */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "scotch.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Strat  s;
  double        v = (argc > 1) ? atof (argv[1]) : 1e300;
  int           r;

  SCOTCH_stratInit (&s); r = SCOTCH_stratGraphMapBuild     (&s, SCOTCH_STRATDEFAULT, 4, v);    printf ("GraphMapBuild      (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); r = SCOTCH_stratGraphClusterBuild (&s, SCOTCH_STRATDEFAULT, 4, v, v); printf ("GraphClusterBuild  (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); r = SCOTCH_stratGraphPartOvlBuild (&s, SCOTCH_STRATDEFAULT, 4, v);    printf ("GraphPartOvlBuild  (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); r = SCOTCH_stratGraphOrderBuild   (&s, SCOTCH_STRATDEFAULT, 0, v);    printf ("GraphOrderBuild    (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); r = SCOTCH_stratMeshOrderBuild    (&s, SCOTCH_STRATDEFAULT, v);       printf ("MeshOrderBuild     (%g) -> %d\n", v, r); SCOTCH_stratExit (&s);
  return (0);
}
