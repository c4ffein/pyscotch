/* Strategy parse/save harness: st '<strategy>' [m|o|e|d|x|y]  (m=graphMap default, o=graphOrder, e=meshOrder, d=graphBipart? no: d=graphPartOvl, x=graphClust) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"
int main (int argc, char * argv[]) {
  SCOTCH_Strat s; int r; char k = (argc > 2) ? argv[2][0] : 'm';
  SCOTCH_errorProg (argv[0]);
  SCOTCH_stratInit (&s);
  switch (k) {
    case 'o' : r = SCOTCH_stratGraphOrder (&s, argv[1]); break;
    case 'e' : r = SCOTCH_stratMeshOrder (&s, argv[1]); break;
    case 'd' : r = SCOTCH_stratGraphPartOvl (&s, argv[1]); break;
    case 'x' : r = SCOTCH_stratGraphClusterBuild (&s, 0, 2, 0.1, 0.05); break;
    default  : r = SCOTCH_stratGraphMap (&s, argv[1]); break;
  }
  printf ("ret=%d\n", r);
  if (r == 0) { SCOTCH_stratSave (&s, stdout); puts (""); }
  SCOTCH_stratExit (&s);
  return (r);
}
