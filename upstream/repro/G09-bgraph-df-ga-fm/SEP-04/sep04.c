/* SEP-04: genetic bipartitioning of a path graph of n vertices.
** n == 2 crashes (SIGFPE in intRandVal) on pristine 7.0.17. */
#include "../common/gridgraph.h"
int main (int argc, char ** argv)
{
  int n = (argc > 1) ? atoi (argv[1]) : 2; const char * st = (argc > 2) ? argv[2] : "r{sep=a{pass=5,pop=8}}";
  SCOTCH_Num * verttab = malloc ((n + 1) * sizeof (SCOTCH_Num)), * edgetab = malloc (2 * n * sizeof (SCOTCH_Num)), edgenbr = 0, * part; int i, o;
  SCOTCH_Graph g; SCOTCH_Strat s;
  for (i = 0; i < n; i ++) { verttab[i] = edgenbr; if (i > 0) edgetab[edgenbr ++] = i - 1; if (i < n - 1) edgetab[edgenbr ++] = i + 1; }
  verttab[n] = edgenbr;
  SCOTCH_graphInit (&g); SCOTCH_graphBuild (&g, 0, n, verttab, NULL, NULL, NULL, edgenbr, edgetab, NULL);
  SCOTCH_stratInit (&s); if (SCOTCH_stratGraphMap (&s, st) != 0) { puts ("parse fail"); return 2; }
  part = calloc (n, sizeof (SCOTCH_Num));
  o = SCOTCH_graphPart (&g, 2, &s, part);
  printf ("rc=%d part:", o); for (i = 0; i < n; i ++) printf (" %d", (int) part[i]); puts ("");
  return (o != 0);
}
