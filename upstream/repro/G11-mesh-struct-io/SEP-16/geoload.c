/* Load a Scotch mesh + geometry file, check, print geometry and save it back. usage: geoload mesh.msh geom.xyz */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[])
{
  SCOTCH_Mesh m; SCOTCH_Geom g; FILE * f0, * f1; int r, c; SCOTCH_Num d, i, n; double * t;
  SCOTCH_meshInit (&m); SCOTCH_geomInit (&g);
  f0 = fopen (argv[1], "r"); f1 = fopen (argv[2], "r");
  r = SCOTCH_meshGeomLoadScot (&m, &g, f0, f1, NULL);
  fclose (f0); fclose (f1);
  c = (r == 0) ? SCOTCH_meshCheck (&m) : -1;
  printf ("load=%d check=%d\n", r, c);
  if (r == 0) {
    SCOTCH_geomData (&g, &d, &t);
    SCOTCH_meshSize (&m, NULL, &n, NULL);
    printf ("dimnnbr=%d\n", (int) d);
    for (i = 0; i < n; i ++) printf ("node %d:", (int) i), printf (d >= 1 ? " %g" : "", t[i * (d > 0 ? d : 1)]), printf (d >= 2 ? " %g\n" : "\n", d >= 2 ? t[i * d + 1] : 0.0);
    printf ("--- saved geometry:\n");
    SCOTCH_meshGeomSaveScot (&m, &g, NULL, stdout, NULL);
    SCOTCH_meshExit (&m);
  }
  SCOTCH_geomExit (&g);
  return (0);
}
