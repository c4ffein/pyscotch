/* PS2-G26-1, meshGraphNodal() instance: SCOTCH_meshBuildElem() + SCOTCH_meshGraph() with the 2nd allocation
** of meshGraphNodal() failing (FAILMALLOC_FUNC=_SCOTCHmeshGraphNodal FAILMALLOC_NTH=2), then SCOTCH_graphExit(). */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Mesh         meshdat;
  SCOTCH_Graph        grafdat;
  SCOTCH_Num          eptr[] = { 0, 3, 6, 9, 12, 15, 18 };
  SCOTCH_Num          eind[] = { 0, 1, 2, 0, 1, 5, 1, 5, 4, 1, 4, 6, 1, 6, 3, 1, 3, 2 };
  int                 o;

  SCOTCH_meshInit  (&meshdat);
  SCOTCH_graphInit (&grafdat);
  if (SCOTCH_meshBuildElem (&meshdat, 0, 0, 6, 7, eptr, eptr + 1, NULL, NULL, NULL, 18, eind) != 0)
    return (2);
  o = SCOTCH_meshGraph (&meshdat, &grafdat);
  printf ("SCOTCH_meshGraph returned %d; now calling SCOTCH_graphExit()\n", o);
  SCOTCH_graphExit (&grafdat);
  SCOTCH_meshExit  (&meshdat);
  printf ("done\n");
  return (0);
}
