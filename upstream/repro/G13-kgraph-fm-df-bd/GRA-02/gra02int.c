/* GRA-02 internal reproducer: kgraphMapFm on a frontier-less, imbalanced mapping with fewer domains than terminals */
#include "internal.h"
int
main (int argc, char * argv[])
{
  int w = (argc > 1) ? atoi (argv[1]) : 16, k = (argc > 2) ? atoi (argv[2]) : 4, d = (argc > 3) ? atoi (argv[3]) : 1;
  Graph g; Arch a; Kgraph kg; static Context ctx; ArchDom root, d0, d1; Gnum i, n = (Gnum) w * w;
  mkgrid (&g, w, w, NULL);
  SCOTCH_archInit ((SCOTCH_Arch *) &a); SCOTCH_archCmplt ((SCOTCH_Arch *) &a, k);
  contextInit (&ctx); contextOptionsInit (&ctx); contextCommit (&ctx);
  if (kgraphInit (&kg, &g, &a, NULL, 0, NULL, 1, 0, NULL) != 0) return (8);
  kg.contptr = &ctx;
  if (mapAlloc (&kg.m) != 0) return (7);
  archDomFrst (&a, &root); archDomBipart (&a, &root, &d0, &d1);
  kg.m.domnnbr = d; kg.m.domntab[0] = d0; if (d > 1) kg.m.domntab[1] = d1; /* d (1 or 2) domains, all vertices in 0: no frontier, imbalance */
  for (i = 0; i < n; i ++) kg.m.parttax[i] = 0;
  kgraphFron (&kg); kgraphCost (&kg);
  printf ("before: domnnbr=%ld fronnbr=%ld dlt0=%ld\n", (long) kg.m.domnnbr, (long) kg.fronnbr, (long) kg.comploaddlt[0]);
  KgraphMapFmParam p = { 200, ~0, 0.05 };
  int r = kgraphMapFm (&kg, &p);
  printf ("after: ret=%d domnnbr=%ld fronnbr=%ld\n", r, (long) kg.m.domnnbr, (long) kg.fronnbr);
  return (0);
}
