/* Try to reach the "graph too small to have any usable anchors" abort of kgraphMapDfLoop()
** with several threads: an n x n grid plus one isolated vertex of large load, mapped onto
** 'parts' parts with the k-way band diffusion strategy; the isolated vertex should get a
** part of its own, whose band anchor then has no edges. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <scotch.h>
int main (int argc, char ** argv)
{
  int n = atoi (argv[1]), thr = atoi (argv[2]), parts = atoi (argv[3]); const char * st = (argc > 4) ? argv[4] : NULL;
  SCOTCH_Num vertnbr = n * n + 1, * verttab = malloc ((vertnbr + 1) * sizeof (SCOTCH_Num)), * edgetab = malloc (4 * vertnbr * sizeof (SCOTCH_Num)), * velotab = malloc (vertnbr * sizeof (SCOTCH_Num)), edgenbr = 0, i, j, * part; long cnt[64] = { 0 }; int o;
  SCOTCH_Graph g0, g; SCOTCH_Context ctx; SCOTCH_Strat s;
  for (i = 0; i < n; i ++) for (j = 0; j < n; j ++) { SCOTCH_Num v = i * n + j; verttab[v] = edgenbr; velotab[v] = 1; if (i > 0) edgetab[edgenbr ++] = v - n; if (j > 0) edgetab[edgenbr ++] = v - 1; if (j < n - 1) edgetab[edgenbr ++] = v + 1; if (i < n - 1) edgetab[edgenbr ++] = v + n; }
  verttab[n * n] = edgenbr; velotab[n * n] = (n * n) / (parts - 1); verttab[vertnbr] = edgenbr; /* Isolated heavy vertex */
  SCOTCH_graphInit (&g0); if (SCOTCH_graphBuild (&g0, 0, vertnbr, verttab, NULL, velotab, NULL, edgenbr, edgetab, NULL) != 0) return 2;
  SCOTCH_contextInit (&ctx); if (thr > 1) SCOTCH_contextThreadSpawn (&ctx, thr, NULL);
  SCOTCH_graphInit (&g); SCOTCH_contextBindGraph (&ctx, &g0, &g);
  SCOTCH_stratInit (&s); if (st != NULL) { if (SCOTCH_stratGraphMap (&s, st) != 0) { puts ("parse fail"); return 2; } }
  part = malloc (vertnbr * sizeof (SCOTCH_Num));
  o = SCOTCH_graphPart (&g, parts, &s, part);
  for (i = 0; i < vertnbr; i ++) cnt[part[i] & 63] ++;
  printf ("rc=%d sizes:", o); for (i = 0; i < parts; i ++) printf (" %ld", cnt[i]); printf (" isolated in part %d\n", (int) part[n * n]);
  return (o != 0);
}
