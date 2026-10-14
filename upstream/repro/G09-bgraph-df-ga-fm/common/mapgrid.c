/* Generic driver: map an n x n grid graph onto a 2D mesh target of 'parts' processors
** (parts/2 x 2), with 'thr' threads and the given mapping strategy. External gain
** arrays (veextax) exist in the bipartition graphs because the target is not complete.
** Optional: vertex load, edge load values, random seed. Prints the return code, the
** part sizes and a hash of the part array. Linked with the non-exiting error library. */
#include "gridgraph.h"
int main (int argc, char ** argv)
{
  int n = atoi (argv[1]), thr = atoi (argv[2]), parts = atoi (argv[3]); const char * st = argv[4];
  SCOTCH_Num velo = (argc > 5) ? atoll (argv[5]) : 0, edlo = (argc > 6) ? atoll (argv[6]) : 0, seed = (argc > 7) ? atoll (argv[7]) : 1;
  SCOTCH_Graph g0, g; SCOTCH_Context ctx; SCOTCH_Strat s; SCOTCH_Arch a; SCOTCH_Mapping m;
  SCOTCH_Num vertnbr = n * n, * part, i; unsigned long hash = 0; long cnt[64] = { 0 }; int o;
  if (gridBuild (&g0, n, velo, edlo) != 0) { puts ("build fail"); return 2; }
  SCOTCH_contextInit (&ctx); if (thr > 1) SCOTCH_contextThreadSpawn (&ctx, thr, NULL);
  if (getenv ("DET") != NULL) SCOTCH_contextOptionSetNum (&ctx, SCOTCH_OPTIONNUMDETERMINISTIC, 1); /* DET=1: deterministic option */
  SCOTCH_contextRandomSeed (&ctx, seed); SCOTCH_contextRandomReset (&ctx);
  SCOTCH_graphInit (&g); SCOTCH_contextBindGraph (&ctx, &g0, &g);
  SCOTCH_archInit (&a); SCOTCH_archMesh2 (&a, (parts / 2 > 0) ? parts / 2 : 1, 2);
  SCOTCH_stratInit (&s); if (SCOTCH_stratGraphMap (&s, st) != 0) { puts ("parse fail"); return 2; }
  part = malloc (vertnbr * sizeof (SCOTCH_Num));
  SCOTCH_graphMapInit (&g, &m, &a, part);
  o = SCOTCH_graphMapCompute (&g, &m, &s);
  for (i = 0; i < vertnbr; i ++) { cnt[part[i] & 63] ++; hash = hash * 31UL + (unsigned long) part[i] + 1UL; }
  printf ("rc=%d sizes:", o); for (i = 0; i < parts; i ++) printf (" %ld", cnt[i]); printf (" hash=%lu\n", hash);
  SCOTCH_graphMapExit (&g, &m); SCOTCH_stratExit (&s); SCOTCH_archExit (&a); SCOTCH_graphExit (&g); SCOTCH_graphExit (&g0); SCOTCH_contextExit (&ctx);
  return (o != 0);
}
