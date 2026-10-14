/* SEP-10 / PS-SEP-5 driver: fixed-vertex mapping of an n x n grid (vertex loads 3) onto
** a complete graph of 'parts' processors: first row fixed to part 0, last row to part 1,
** others free; strategy given. Linked with the non-exiting error library. */
#include "gridgraph.h"
int main (int argc, char ** argv)
{
  const char * st = argv[1]; int n = (argc > 2) ? atoi (argv[2]) : 12, parts = (argc > 3) ? atoi (argv[3]) : 2;
  SCOTCH_Graph g; SCOTCH_Arch a; SCOTCH_Strat s; SCOTCH_Mapping m;
  SCOTCH_Num vertnbr = n * n, * part, i; int o;
  if (gridBuild (&g, n, 3, 0) != 0) { puts ("build fail"); return 2; }
  SCOTCH_archInit (&a); SCOTCH_archCmplt (&a, parts);
  SCOTCH_stratInit (&s); if (SCOTCH_stratGraphMap (&s, st) != 0) { puts ("parse fail"); return 2; }
  part = malloc (vertnbr * sizeof (SCOTCH_Num));
  for (i = 0; i < vertnbr; i ++) part[i] = -1;
  for (i = 0; i < n; i ++) { part[i] = 0; part[vertnbr - 1 - i] = 1; }
  SCOTCH_graphMapInit (&g, &m, &a, part);
  o = SCOTCH_graphMapFixedCompute (&g, &m, &s);
  printf ("rc=%d part[0]=%d part[last]=%d\n", o, (int) part[0], (int) part[vertnbr - 1]);
  SCOTCH_graphMapExit (&g, &m); SCOTCH_stratExit (&s); SCOTCH_archExit (&a); SCOTCH_graphExit (&g);
  return (o != 0);
}
