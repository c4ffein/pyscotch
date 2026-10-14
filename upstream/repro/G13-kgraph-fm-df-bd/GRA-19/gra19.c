/* GRA-19: build a band graph (kgraphBand) around a 2-part mapping onto cmplt(4): parts 2,3 are empty,
** so their anchors are isolated; print the load targets kgraphCost computes for the band graph */
#include "internal.h"
#include "kgraph_band.h"
int
main (int argc, char * argv[])
{
  int w = 16; Gnum n = (Gnum) w * w, i; Anum d;
  Graph g; Arch a; Kgraph kg, bnd; static Context ctx; ArchDom dom[4]; Gnum bndvertlvlnum; Gnum * bndvnumtax;
  mkgrid (&g, w, w, NULL);
  SCOTCH_archInit ((SCOTCH_Arch *) &a); SCOTCH_archCmplt ((SCOTCH_Arch *) &a, 4);
  contextInit (&ctx); contextOptionsInit (&ctx); contextCommit (&ctx);
  if (kgraphInit (&kg, &g, &a, NULL, 0, NULL, 1, 0, NULL) != 0) return (8);
  kg.contptr = &ctx; if (mapAlloc (&kg.m) != 0) return (7);
  for (d = 0; d < 4; d ++) archDomTerm (&a, &dom[d], d);
  kg.m.domnnbr = 4; for (d = 0; d < 4; d ++) kg.m.domntab[d] = dom[d];
  for (i = 0; i < n; i ++) kg.m.parttax[i] = ((i / w) < w / 2) ? 0 : 1; /* Parts 2 and 3 empty */
  kgraphFron (&kg); kgraphCost (&kg);
  printf ("orig : velosum=%ld avg", (long) kg.s.velosum); for (d = 0; d < 4; d ++) printf (" %ld", (long) kg.comploadavg[d]);
  printf (" dlt"); for (d = 0; d < 4; d ++) printf (" %ld", (long) kg.comploaddlt[d]); printf ("\n");
  if (kgraphBand (&kg, 3, &bnd, &bndvertlvlnum, &bndvnumtax) != 0) return (6);
  { Gnum anc = bnd.s.vertnnd - 4, sa = 0, sd = 0; printf ("band : vertnbr=%ld velosum=%ld anchors deg/velo:", (long) bnd.s.vertnbr, (long) bnd.s.velosum);
    for (d = 0; d < 4; d ++) printf (" %ld/%ld", (long) (bnd.s.vendtax[anc + d] - bnd.s.verttax[anc + d]), (long) bnd.s.velotax[anc + d]);
    printf ("\nband : avg"); for (d = 0; d < 4; d ++) { printf (" %ld", (long) bnd.comploadavg[d]); sa += bnd.comploadavg[d]; }
    printf (" dlt"); for (d = 0; d < 4; d ++) { printf (" %ld", (long) bnd.comploaddlt[d]); sd += bnd.comploaddlt[d]; }
    printf ("  sum(avg)=%ld sum(dlt)=%ld\n", (long) sa, (long) sd); }
  return (0);
}
