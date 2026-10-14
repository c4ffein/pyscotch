/* SEP-03 / PS-SEP-4: SCOTCH_meshOrder on NE disjoint triangles (each element has 3 private nodes).
** usage: sep03 NE [baseval] ; STRAT env overrides the strategy. */
#include <stdio.h>
#include <stdlib.h>
#include <scotch.h>
typedef SCOTCH_Num Num;
int
main (int argc, char ** argv)
{
  int ne = (argc > 1) ? atoi (argv[1]) : 300, nn = 3 * ne, i, j, r; Num nv = ne + nn, e = 0, baseval = (argc > 2) ? atoi (argv[2]) : 1;
  Num * vt = malloc ((nv + 1) * sizeof (Num)), * ed = malloc (6 * ne * sizeof (Num)), * perm, * peri;
  SCOTCH_Mesh m; SCOTCH_Strat s;
  for (i = 0; i < ne; i ++) { vt[i] = e + baseval; for (j = 0; j < 3; j ++) ed[e ++] = ne + baseval + 3 * i + j; }
  for (i = 0; i < nn; i ++) { vt[ne + i] = e + baseval; ed[e ++] = i / 3 + baseval; }
  vt[nv] = e + baseval;
  SCOTCH_meshInit (&m);
  if (SCOTCH_meshBuild (&m, baseval, ne + baseval, ne, nn, vt, vt + 1, NULL, NULL, NULL, e, ed) != 0) { puts ("build fail"); return (1); }
  if (SCOTCH_meshCheck (&m) != 0) { puts ("check fail"); return (1); }
  SCOTCH_stratInit (&s);
  if (getenv ("STRAT") != NULL) SCOTCH_stratMeshOrder (&s, getenv ("STRAT"));
  perm = malloc (nn * sizeof (Num)); peri = malloc (nn * sizeof (Num));
  r = SCOTCH_meshOrder (&m, &s, perm, peri, NULL, NULL, NULL);
  if (r != 0) { printf ("order=%d (failed)\n", r); SCOTCH_stratExit (&s); SCOTCH_meshExit (&m); free (perm); free (peri); free (vt); free (ed); return (r); }
  printf ("ne=%d base=%ld order=%d\n", ne, (long) baseval, r);
  { char * seen = calloc (nn, 1); int bad = 0; for (i = 0; i < nn; i ++) { if (peri[i] < baseval || peri[i] >= nn + baseval || seen[peri[i] - baseval]) bad = 1; else seen[peri[i] - baseval] = 1; }
    for (i = 0; i < nn; i ++) if (perm[peri[i] - baseval] != i + baseval) bad = 1;
    printf ("permutation %s\n", bad ? "INVALID" : "valid"); free (seen); if (bad) return (1); }
  SCOTCH_stratExit (&s); SCOTCH_meshExit (&m); free (perm); free (peri); free (vt); free (ed);
  return (r);
}
