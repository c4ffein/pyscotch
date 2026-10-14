/* GRA-12: two disjoint grids mapped onto cmplt(4); parts 2 and 3 are empty so their anchors
** become isolated in the band graph. kgraphMapBd(bnd=d{pass=N}) with THR threads; thread owning
** an empty-part anchor jumps to fail: before the two setup barriers -> the others hang. */
#include "internal.h"
extern int SCOTCH_contextThreadSpawn (SCOTCH_Context *, int, const int *);
int
main (int argc, char * argv[])
{
  int W1 = 14, W2 = 7, H = 14, thr = atoi (argv[1]);
  Gnum n1 = (Gnum) W1 * H, n2 = (Gnum) W2 * H, n = n1 + n2, i, e = 0;
  Gnum * vt = malloc ((n + 1) * sizeof (Gnum));
  Gnum * et = malloc (4 * n * sizeof (Gnum));
  Graph g; Arch a; Kgraph kg; static Context ctx; ArchDom dom[4]; Anum d;
  for (i = 0; i < n; i ++) {
    int base = (i < n1) ? 0 : n1, W = (i < n1) ? W1 : W2, nn = (i < n1) ? n1 : n2, j = i - base, x = j % W, y = j / W;
    vt[i] = e;
    if (x > 0)     et[e ++] = i - 1;
    if (x < W - 1) et[e ++] = i + 1;
    if (y > 0)     et[e ++] = i - W;
    if (j + W < nn) et[e ++] = i + W;
  }
  vt[n] = e;
  SCOTCH_graphInit ((SCOTCH_Graph *) &g);
  if (SCOTCH_graphBuild ((SCOTCH_Graph *) &g, 0, n, vt, NULL, NULL, NULL, e, et, NULL) != 0) return (9);
  SCOTCH_archInit ((SCOTCH_Arch *) &a); SCOTCH_archCmplt ((SCOTCH_Arch *) &a, 4);
  contextInit (&ctx); contextOptionsInit (&ctx);
  if (thr > 1) { if (SCOTCH_contextThreadSpawn ((SCOTCH_Context *) &ctx, thr, NULL) != 0) { puts ("spawn fail"); return (2); } }
  else contextCommit (&ctx);
  if (kgraphInit (&kg, &g, &a, NULL, 0, NULL, 1, 0, NULL) != 0) return (8);
  kg.contptr = &ctx; if (mapAlloc (&kg.m) != 0) return (7);
  for (d = 0; d < 4; d ++) archDomTerm (&a, &dom[d], d);
  kg.m.domnnbr = 4; for (d = 0; d < 4; d ++) kg.m.domntab[d] = dom[d];
  for (i = 0; i < n; i ++) kg.m.parttax[i] = (i >= n1) ? 1 : (((i / W1) < H / 2) ? 0 : 1); /* parts 2,3 empty */
  kgraphFron (&kg); kgraphCost (&kg);
  printf ("fronnbr=%ld domnnbr=%ld\n", (long) kg.fronnbr, (long) kg.m.domnnbr); fflush (stdout);
  KgraphMapBdParam p; p.distmax = 3;
  p.stratbnd = stratInit (&kgraphmapststratab, "d{pass=10}");
  p.stratorg = stratInit (&kgraphmapststratab, "");
  int r = kgraphMapBd (&kg, &p);
  printf ("ret=%d\n", r);
  return (0);
}
