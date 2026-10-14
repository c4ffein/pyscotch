/* SEP-02: SCOTCH_meshOrder on an element-weighted mesh built with SCOTCH_meshBuild.
** usage: sep02 N kind [baseval]   kind: 1 = element loads, 2 = node loads, 3 = both */
#include "../common/meshgrid.h"
int
main (int argc, char ** argv)
{
  SCOTCH_Mesh m; SCOTCH_Strat s; Num nn, velosum, vnlosum, * perm, * peri; int r, i, N, kind; Num baseval;
  unsigned long h = 0;
  N = (argc > 1) ? atoi (argv[1]) : 30; kind = (argc > 2) ? atoi (argv[2]) : 1; baseval = (argc > 3) ? atoi (argv[3]) : 0;
  SCOTCH_meshInit (&m);
  if (buildgrid (&m, N, kind, baseval, &nn, &velosum, &vnlosum) != 0) { puts ("build fail"); return (1); }
  if (SCOTCH_meshCheck (&m) != 0) { puts ("check fail"); return (1); }
  SCOTCH_stratInit (&s);
  if (getenv ("STRAT") != NULL) SCOTCH_stratMeshOrder (&s, getenv ("STRAT"));
  perm = malloc (nn * sizeof (Num)); peri = malloc (nn * sizeof (Num));
  r = SCOTCH_meshOrder (&m, &s, perm, peri, NULL, NULL, NULL);
  if (r != 0) { printf ("order=%d (failed)\n", r); SCOTCH_stratExit (&s); SCOTCH_meshExit (&m); free (perm); free (peri); gridfree (); return (r); }
  for (i = 0; i < nn; i ++) h = h * 1000003UL + (unsigned long) peri[i];
  printf ("N=%d kind=%d base=%ld order=%d hash=%lx\n", N, kind, (long) baseval, r, h);
  { char * seen = calloc (nn, 1); int bad = 0; for (i = 0; i < nn; i ++) { if (peri[i] < baseval || peri[i] >= nn + baseval || seen[peri[i] - baseval]) bad = 1; else seen[peri[i] - baseval] = 1; }
    for (i = 0; i < nn; i ++) if (perm[peri[i] - baseval] != i + baseval) bad = 1;
    printf ("permutation %s\n", bad ? "INVALID" : "valid"); free (seen); if (bad) return (1); }
  SCOTCH_stratExit (&s); SCOTCH_meshExit (&m); free (perm); free (peri); gridfree ();
  return (r);
}
