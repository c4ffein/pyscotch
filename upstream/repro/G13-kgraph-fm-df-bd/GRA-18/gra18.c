/* GRA-18: kgraphMapBd with bnd=d{pass=N} on a 2-part jagged mapping of a WxW grid; count changed vertices */
#include "internal.h"
int
main (int argc, char * argv[])
{
  int w = 24, passes = atoi (argv[1]); Gnum n = (Gnum) w * w, i;
  Graph g; Arch a; Kgraph kg; static Context ctx; ArchDom root, d0, d1; Anum * orig = malloc (n * sizeof (Anum));
  mkgrid (&g, w, w, NULL);
  SCOTCH_archInit ((SCOTCH_Arch *) &a); SCOTCH_archCmplt ((SCOTCH_Arch *) &a, 2);
  contextInit (&ctx); contextOptionsInit (&ctx); contextCommit (&ctx);
  if (kgraphInit (&kg, &g, &a, NULL, 0, NULL, 1, 0, NULL) != 0) return (8);
  kg.contptr = &ctx; if (mapAlloc (&kg.m) != 0) return (7);
  archDomFrst (&a, &root); archDomBipart (&a, &root, &d0, &d1);
  kg.m.domnnbr = 2; kg.m.domntab[0] = d0; kg.m.domntab[1] = d1;
  for (i = 0; i < n; i ++) { int x = i % w, y = i / w; orig[i] = kg.m.parttax[i] = ((x + (y % 3)) < w / 2) ? 0 : 1; }
  kgraphFron (&kg); kgraphCost (&kg);
  KgraphMapBdParam p; char buf[64]; sprintf (buf, "d{pass=%d}", passes);
  p.distmax = 4; p.stratbnd = stratInit (&kgraphmapststratab, buf); p.stratorg = stratInit (&kgraphmapststratab, "");
  Gnum cut0 = kg.commload; int r = kgraphMapBd (&kg, &p);
  int ch = 0; for (i = 0; i < n; i ++) if (kg.m.parttax[i] != orig[i]) ch ++;
  printf ("pass=%d ret=%d changed=%d cut %ld -> %ld\n", passes, r, ch, (long) cut0, (long) kg.commload);
  return (0);
}
