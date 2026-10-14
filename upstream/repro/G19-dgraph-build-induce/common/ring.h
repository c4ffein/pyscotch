/* Bidirectional ring of nl vertices per process, base b. ring_setup() allocates and fills the arrays (before the fault
   injector is armed: the shim counts every allocation made from a path containing "scotch", including this program's),
   ring_build() calls SCOTCH_dgraphBuild() on them. Arrays are leaked on purpose. */
static SCOTCH_Num * ring_vert, * ring_edge, * ring_edlo;
static void
ring_setup (int rank, int np, int b, int nl, int withedlo)
{
  SCOTCH_Num N = (SCOTCH_Num) nl * np, lo = (SCOTCH_Num) nl * rank;
  int i;
  ring_vert = malloc ((nl + 1) * sizeof (SCOTCH_Num)); ring_edge = malloc ((2 * nl + 1) * sizeof (SCOTCH_Num));
  ring_edlo = withedlo ? malloc ((2 * nl + 1) * sizeof (SCOTCH_Num)) : NULL;
  for (i = 0; i < nl; i ++) {
    SCOTCH_Num gv = lo + i;
    ring_vert[i] = b + 2 * i;
    ring_edge[2 * i]     = b + (gv + N - 1) % N;
    ring_edge[2 * i + 1] = b + (gv + 1) % N;
    if (withedlo) { ring_edlo[2 * i] = 1 + (int) ((gv + N - 1) % N + gv) % 5; ring_edlo[2 * i + 1] = 1 + (int) (gv + (gv + 1) % N) % 5; }
  }
  ring_vert[nl] = b + 2 * nl;
}
static int
ring_build (SCOTCH_Dgraph * g, int b, int nl)
{
  return (SCOTCH_dgraphBuild (g, b, nl, nl, ring_vert, NULL, NULL, NULL, 2 * nl, 2 * nl, ring_edge, NULL, ring_edlo));
}
