/* API-22: SCOTCH_graphPartOvlView must return 1 when its work arrays cannot
** be allocated. usage: po [partnbr]  (default 2; use a huge value such as
** 68719476736 on a 64-bit Gnum build with ASAN_OPTIONS=allocator_may_return_null=1,
** or FAIL_NTH=<n> with the failmalloc.so preload on the plain build). */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Num          parttab[4] = { 0, 0, 1, 1 };
  SCOTCH_Num          partnbr = (argc > 1) ? (SCOTCH_Num) atoll (argv[1]) : 2;
  int                 r;

  mkpath (&g, 4, NULL, 1);
  r = SCOTCH_graphPartOvlView (&g, partnbr, parttab, stdout);
  printf ("r=%d\n", r);
  return (0);
}
