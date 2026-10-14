/* Load a Harwell-Boeing elemental matrix as a mesh and check it. usage: hbload file [tag] */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[])
{
  SCOTCH_Mesh m; SCOTCH_Geom g; FILE * f; int r, c;
  SCOTCH_meshInit (&m); SCOTCH_geomInit (&g);
  f = fopen (argv[1], "r");
  r = SCOTCH_meshGeomLoadHabo (&m, &g, f, NULL, (argc > 2) ? argv[2] : "0");
  fclose (f);
  c = (r == 0) ? SCOTCH_meshCheck (&m) : -1;
  printf ("load=%d check=%d\n", r, c);
  if (r == 0) { SCOTCH_meshSave (&m, stdout); SCOTCH_meshExit (&m); }
  SCOTCH_geomExit (&g);
  return (0);
}
