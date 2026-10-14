/* Build an N x N quad mesh (elements first, base baseval) through SCOTCH_meshBuild.
** velotab (element loads) is placed just below an mprotect()ed guard page so that any
** read of velotab[k], k >= ne, faults immediately instead of landing in live heap. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <scotch.h>

typedef SCOTCH_Num Num;

static void *
guardalloc (size_t sz)
{
  size_t pg = 4096, n = (sz + pg - 1) / pg + 1;
  char * b = mmap (0, (n + 1) * pg, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (b == MAP_FAILED) { perror ("mmap"); exit (2); }
  mprotect (b + n * pg, pg, PROT_NONE);
  return (b + n * pg - sz);
}

/* kind bits: 1 = element loads, 2 = node loads */
static Num * grid_vt, * grid_cnt, * grid_eg, * grid_fill, * grid_nlo;  /* Kept to be freed by gridfree() */
static void
gridfree (void)
{
  free (grid_vt); free (grid_cnt); free (grid_eg); free (grid_fill); free (grid_nlo);
}

static int
buildgrid (SCOTCH_Mesh * m, int N, int kind, Num baseval, Num * nnptr, Num * velosumptr, Num * vnlosumptr)
{
  int ne = N * N, nn = (N + 1) * (N + 1), i, j;
  Num * vt = malloc ((ne + nn + 1) * sizeof (Num));
  Num * cnt = calloc (nn, sizeof (Num));
  Num pos, tot, * eg, * fill, * vlo = NULL, * nlo = NULL;
  Num velosum = 0, vnlosum = 0;
  for (i = 0; i < ne; i ++) { int ei = i / N, ej = i % N; int ns[4] = { ei * (N + 1) + ej, ei * (N + 1) + ej + 1, (ei + 1) * (N + 1) + ej, (ei + 1) * (N + 1) + ej + 1 }; for (j = 0; j < 4; j ++) cnt[ns[j]] ++; }
  pos = baseval; for (i = 0; i < ne; i ++) { vt[i] = pos; pos += 4; }
  for (i = 0; i < nn; i ++) { vt[ne + i] = pos; pos += cnt[i]; }
  vt[ne + nn] = pos; tot = pos - baseval;
  eg = malloc (tot * sizeof (Num)); fill = calloc (nn, sizeof (Num));
  for (i = 0; i < ne; i ++) { int ei = i / N, ej = i % N; int ns[4] = { ei * (N + 1) + ej, ei * (N + 1) + ej + 1, (ei + 1) * (N + 1) + ej, (ei + 1) * (N + 1) + ej + 1 };
    for (j = 0; j < 4; j ++) { eg[vt[i] - baseval + j] = ne + ns[j] + baseval; eg[vt[ne + ns[j]] - baseval + fill[ns[j]] ++] = i + baseval; } }
  if (kind & 1) { vlo = guardalloc (ne * sizeof (Num)); for (i = 0; i < ne; i ++) { vlo[i] = 1 + i % 3; velosum += vlo[i]; } }
  if (kind & 2) { nlo = malloc (nn * sizeof (Num)); for (i = 0; i < nn; i ++) { nlo[i] = 1 + i % 5; vnlosum += nlo[i]; } }
  *nnptr = nn; *velosumptr = velosum; *vnlosumptr = vnlosum;
  grid_vt = vt; grid_cnt = cnt; grid_eg = eg; grid_fill = fill; grid_nlo = nlo;
  return (SCOTCH_meshBuild (m, baseval, ne + baseval, ne, nn, vt, vt + 1, vlo, nlo, NULL, tot, eg));
}
