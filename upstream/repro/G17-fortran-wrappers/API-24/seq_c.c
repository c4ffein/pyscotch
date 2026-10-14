/* C twin of seq_f.f90: prints the reference MESHSTAT and SIZEOF lines. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int main (void)
{
  SCOTCH_Mesh meshdat;
  SCOTCH_Num verttab[12] = { 1, 5, 9, 13, 14, 16, 18, 20, 21, 22, 23, 25 };
  SCOTCH_Num edgetab[24] = { 5, 11, 7, 6, 10, 5, 11, 4, 8, 9, 6, 7, 2, 2, 1, 1, 3, 1, 3, 3, 3, 2, 2, 1 };
  SCOTCH_Num vnlomin, vnlomax, vnlosum, edegmin, edegmax, ndegmin, ndegmax;
  double vnloavg, vnlodlt, edegavg, edegdlt, ndegavg, ndegdlt;

  if (SCOTCH_meshInit (&meshdat) != 0 ||
      SCOTCH_meshBuild (&meshdat, 1, 4, 3, 8, verttab, NULL, NULL, NULL, NULL, 24, edgetab) != 0 ||
      SCOTCH_meshCheck (&meshdat) != 0) {
    fprintf (stderr, "ERROR: mesh\n");
    return (1);
  }
  SCOTCH_meshStat (&meshdat, &vnlomin, &vnlomax, &vnlosum, &vnloavg, &vnlodlt, &edegmin, &edegmax, &edegavg, &edegdlt,
                   &ndegmin, &ndegmax, &ndegavg, &ndegdlt);
  printf ("MESHSTAT %ld %ld %ld %ld %ld %ld %ld %10.4f %10.4f %10.4f %10.4f %10.4f %10.4f\n",
          (long) vnlomin, (long) vnlomax, (long) vnlosum, (long) edegmin, (long) edegmax, (long) ndegmin, (long) ndegmax,
          vnloavg, vnlodlt, edegavg, edegdlt, ndegavg, ndegdlt);
  SCOTCH_meshExit (&meshdat);
  printf ("SIZEOF strat %d\n", SCOTCH_stratSizeof ());
  printf ("SIZEOF map %d\n", SCOTCH_mapSizeof ());
  printf ("SIZEOF order %d\n", SCOTCH_orderSizeof ());
  return (0);
}
