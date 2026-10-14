/* GRA-20: kgraphMapBd on a 2-domain mapping onto cmplt(8) with a band strategy that re-maps from scratch (creates 8 domains) */
#include "internal.h"
int
main (int argc, char * argv[])
{
  int w = 24; Gnum n = (Gnum) w * w, i;
  Graph g; Arch a; Kgraph kg; static Context ctx; ArchDom root, d0, d1; Anum * orig = malloc (n * sizeof (Anum));
  mkgrid (&g, w, w, NULL);
  SCOTCH_archInit ((SCOTCH_Arch *) &a); SCOTCH_archCmplt ((SCOTCH_Arch *) &a, 8);
  contextInit (&ctx); contextOptionsInit (&ctx); contextCommit (&ctx);
  if (kgraphInit (&kg, &g, &a, NULL, 0, NULL, 1, 0, NULL) != 0) return (8);
  kg.contptr = &ctx; if (mapAlloc (&kg.m) != 0) return (7);
  archDomFrst (&a, &root); archDomBipart (&a, &root, &d0, &d1);
  kg.m.domnnbr = 2; kg.m.domntab[0] = d0; kg.m.domntab[1] = d1;
  for (i = 0; i < n; i ++) { int x = i % w, y = i / w; orig[i] = kg.m.parttax[i] = ((x + (y % 3)) < w / 2) ? 0 : 1; }
  kgraphFron (&kg); kgraphCost (&kg);
  KgraphMapBdParam p;
  p.distmax = 4; p.stratbnd = stratInit (&kgraphmapststratab, (argc > 1) ? argv[1] : "r{sep=h{pass=10}}"); p.stratorg = stratInit (&kgraphmapststratab, "");
  int r = kgraphMapBd (&kg, &p);
  int ch = 0; Anum pmax = 0; for (i = 0; i < n; i ++) { if (kg.m.parttax[i] != orig[i]) ch ++; if (kg.m.parttax[i] > pmax) pmax = kg.m.parttax[i]; }
  printf ("ret=%d changed=%d domnnbr=%ld maxpart=%ld\n", r, ch, (long) kg.m.domnnbr, (long) pmax);
  return (0);
}
