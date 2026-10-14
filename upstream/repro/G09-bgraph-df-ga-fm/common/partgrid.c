/* DET=1 in the environment sets the deterministic context option.
** Generic driver: bipartition/partition an n x n grid into 'parts' parts with a strategy
** and 'thr' threads, 'runs' times with the same seed; prints rc and the number of distinct
** results (1 = deterministic). Linked with the non-exiting error library. */
#include "gridgraph.h"
int main (int argc, char ** argv)
{
  int n = atoi (argv[1]), thr = atoi (argv[2]), parts = atoi (argv[3]); const char * st = argv[4]; int runs = (argc > 5) ? atoi (argv[5]) : 1;
  SCOTCH_Graph g0, g; SCOTCH_Context ctx; SCOTCH_Strat s; SCOTCH_Num * part, * ref, vertnbr = n * n, i; int r, o = 0, distinct = 1;
  if (gridBuild (&g0, n, 0, 0) != 0) { puts ("build fail"); return 2; }
  SCOTCH_contextInit (&ctx); if (thr > 1) SCOTCH_contextThreadSpawn (&ctx, thr, NULL);
  if (getenv ("DET") != NULL) SCOTCH_contextOptionSetNum (&ctx, SCOTCH_OPTIONNUMDETERMINISTIC, 1); /* DET=1: deterministic option */
  SCOTCH_graphInit (&g); SCOTCH_contextBindGraph (&ctx, &g0, &g);
  SCOTCH_stratInit (&s); if (SCOTCH_stratGraphMap (&s, st) != 0) { puts ("parse fail"); return 2; }
  part = malloc (vertnbr * sizeof (SCOTCH_Num)); ref = malloc (vertnbr * sizeof (SCOTCH_Num));
  for (r = 0; r < runs; r ++) {
    long cnt[64] = { 0 }; unsigned long hash = 0;
    SCOTCH_contextRandomSeed (&ctx, 42); SCOTCH_contextRandomReset (&ctx);
    o |= SCOTCH_graphPart (&g, parts, &s, part);
    for (i = 0; i < vertnbr; i ++) { cnt[part[i] & 63] ++; hash = hash * 31UL + (unsigned long) part[i] + 1UL; }
    if (r == 0) { memcpy (ref, part, vertnbr * sizeof (SCOTCH_Num)); printf ("rc=%d sizes:", o); for (i = 0; i < parts; i ++) printf (" %ld", cnt[i]); printf (" hash=%lu\n", hash); }
    else if (memcmp (ref, part, vertnbr * sizeof (SCOTCH_Num)) != 0) distinct ++;
  }
  printf ("threads=%d runs=%d distinct_results=%d\n", thr, runs, distinct);
  SCOTCH_stratExit (&s); SCOTCH_graphExit (&g); SCOTCH_graphExit (&g0); SCOTCH_contextExit (&ctx);
  return (o != 0);
}
