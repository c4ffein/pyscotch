#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (void) {
  SCOTCH_Strat s;
  SCOTCH_stratInit (&s); SCOTCH_stratGraphMapBuild (&s, SCOTCH_STRATDEFAULT, 16, 0.03); printf ("m "); SCOTCH_stratSave (&s, stdout); puts (""); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); SCOTCH_stratGraphOrderBuild (&s, SCOTCH_STRATDEFAULT, 0, 0.2); printf ("o "); SCOTCH_stratSave (&s, stdout); puts (""); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); SCOTCH_stratMeshOrderBuild (&s, SCOTCH_STRATDEFAULT, 0.2); printf ("e "); SCOTCH_stratSave (&s, stdout); puts (""); SCOTCH_stratExit (&s);
  SCOTCH_stratInit (&s); SCOTCH_stratGraphMap (&s, "r{sep=/(vert>(10+2)*3)?m{asc=b{width=3,org=f,bnd=f},low=h{pass=10}f{move=120,pass=-1,bal=0.01}};b{bnd=f,org=f}}"); printf ("m "); SCOTCH_stratSave (&s, stdout); puts (""); SCOTCH_stratExit (&s);
  return 0;
}
