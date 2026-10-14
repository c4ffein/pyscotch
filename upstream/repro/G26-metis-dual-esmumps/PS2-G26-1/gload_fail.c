/* PS2-G26-1 reproducer: SCOTCH_graphLoad() / SCOTCH_graphGeomLoadChac() / SCOTCH_meshGraphDual()
** followed by SCOTCH_graphExit() when an allocation fails (LD_PRELOAD failmalloc.so with
** FAILMALLOC_FUNC=_SCOTCHmemAllocGroup or _SCOTCHmeshGraphDual, FAILMALLOC_NTH=2).
** Linked with the non-exiting error library, as library users do. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        grafdat;
  SCOTCH_Geom         geomdat;
  FILE *              stream;
  int                 o;

  SCOTCH_graphInit (&grafdat);
  SCOTCH_geomInit  (&geomdat);
  stream = fopen (argv[2], "r");
  if (argv[1][0] == 'c')
    o = SCOTCH_graphGeomLoadChac (&grafdat, &geomdat, stream, NULL, NULL);
  else
    o = SCOTCH_graphLoad (&grafdat, stream, -1, 0);
  printf ("load returned %d; now calling SCOTCH_graphExit()\n", o);
  SCOTCH_graphExit (&grafdat);
  SCOTCH_geomExit  (&geomdat);
  printf ("done\n");
  return (0);
}
