/* Context-bound handles. usage: bound mode mesh.msh ; mode 0: graphDump on a bound graph;
   mode 1: meshGraph into a bound output graph; mode 2: meshGeomLoadScot on a bound mesh container;
   mode 3: meshExit on a bound mesh container (must be a no-op like graphExit) */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[])
{
  SCOTCH_Mesh m, mc; SCOTCH_Graph g, gc; SCOTCH_Context ctx; SCOTCH_Geom geo; FILE * f; int mode = atoi (argv[1]);
  SCOTCH_Num vertnbr = -1;
  SCOTCH_contextInit (&ctx);
  SCOTCH_meshInit (&m); SCOTCH_graphInit (&g); SCOTCH_geomInit (&geo);
  if (mode != 2) { f = fopen (argv[2], "r"); if (SCOTCH_meshLoad (&m, f, -1) != 0) return 2; fclose (f); }
  if (mode == 0) {
    if (SCOTCH_meshGraph (&m, &g) != 0) return 3;
    SCOTCH_contextBindGraph (&ctx, &g, &gc);
    SCOTCH_graphDump (&gc, "p", "s", stdout);
  }
  else if (mode == 1) {
    SCOTCH_contextBindGraph (&ctx, &g, &gc);
    printf ("meshGraph=%d\n", SCOTCH_meshGraph (&m, &gc));
    SCOTCH_graphSize (&g, &vertnbr, NULL);
    printf ("underlying graph vertnbr=%d check=%d\n", (int) vertnbr, SCOTCH_graphCheck (&g));
  }
  else if (mode == 2) {
    SCOTCH_contextBindMesh (&ctx, &m, &mc);
    f = fopen (argv[2], "r");
    printf ("meshGeomLoadScot(container)=%d\n", SCOTCH_meshGeomLoadScot (&mc, &geo, f, NULL, NULL));
    fclose (f);
    SCOTCH_meshSize (&m, NULL, &vertnbr, NULL);
    printf ("underlying mesh vnodnbr=%d check=%d\n", (int) vertnbr, SCOTCH_meshCheck (&m));
  }
  else if (mode == 3) {
    SCOTCH_contextBindMesh (&ctx, &m, &mc);
    SCOTCH_meshExit (&mc);                         /* Should be a no-op on a container */
    printf ("meshExit(container) done; underlying check=%d\n", SCOTCH_meshCheck (&m));
  }
  SCOTCH_meshExit (&m); SCOTCH_graphExit (&g); SCOTCH_contextExit (&ctx);
  return (0);
}
