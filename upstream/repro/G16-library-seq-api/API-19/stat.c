/* API-19: SCOTCH_graphStat edlosum convention.
** 4-vertex path (3 edges, 6 arcs), built three times:
**   (a) without edge loads, (b) with explicit unit loads, (c) with loads 2,5,3.
** (a) and (b) describe the same graph and must report the same edlosum.
** Expected after the fix (each edge counted once): 3, 3, 10.
*/

#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

static SCOTCH_Num
stat (const SCOTCH_Num * const edlotab, double * const avgptr)
{
  SCOTCH_Graph grafdat;
  SCOTCH_Num   verttab[5] = { 0, 1, 3, 5, 6 };
  SCOTCH_Num   edgetab[6] = { 1, 0, 2, 1, 3, 2 };
  SCOTCH_Num   velomin, velomax, velosum, degrmin, degrmax, edlomin, edlomax, edlosum;
  double       veloavg, velodlt, degravg, degrdlt, edloavg, edlodlt;

  SCOTCH_graphInit (&grafdat);
  if ((SCOTCH_graphBuild (&grafdat, 0, 4, verttab, NULL, NULL, NULL, 6, edgetab, (SCOTCH_Num *) edlotab) != 0) ||
      (SCOTCH_graphCheck (&grafdat) != 0)) {
    fprintf (stderr, "cannot build graph\n");
    exit (EXIT_FAILURE);
  }
  SCOTCH_graphStat (&grafdat, &velomin, &velomax, &velosum, &veloavg, &velodlt,
                    &degrmin, &degrmax, &degravg, &degrdlt,
                    &edlomin, &edlomax, &edlosum, &edloavg, &edlodlt);
  SCOTCH_graphExit (&grafdat);
  *avgptr = edloavg;
  return (edlosum);
}

int
main (void)
{
  const SCOTCH_Num edloone[6] = { 1, 1, 1, 1, 1, 1 };
  const SCOTCH_Num edlowgt[6] = { 2, 2, 5, 5, 3, 3 };
  SCOTCH_Num       suma, sumb, sumc;
  double           avga, avgb, avgc;
  int              o;

  suma = stat (NULL,    &avga);
  sumb = stat (edloone, &avgb);
  sumc = stat (edlowgt, &avgc);
  o = ((suma != 3) || (sumb != 3) || (sumc != 10) || (avga != 1.0) || (avgb != 1.0) || (avgc != 10.0 / 3.0));
  printf ("no loads:   edlosum=%ld avg=%g (expected 3, 1)\n",  (long) suma, avga);
  printf ("unit loads: edlosum=%ld avg=%g (expected 3, 1)\n",  (long) sumb, avgb);
  printf ("loads 2,5,3: edlosum=%ld avg=%g (expected 10, 3.33333)\n", (long) sumc, avgc);
  printf ("%s\n", o ? "FAIL" : "ok");
  return (o ? EXIT_FAILURE : EXIT_SUCCESS);
}
