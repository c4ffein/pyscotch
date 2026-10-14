/* GRA-01: SCOTCH_graphMapFixed with many zero-weight fixed vertices on
** distinct terminals and few free vertices.
** usage: gra01 fixnbr fixweight [freenbr]   (hangs on pristine 7.0.17 when
** fixweight == 0 and fixnbr > 4 * 2^bits(freenbr)) */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Arch         a;
  SCOTCH_Strat        s;
  SCOTCH_Num          nf   = atol (argv[1]);
  SCOTCH_Num          w0   = atol (argv[2]);
  SCOTCH_Num          nfree = (argc > 3) ? atol (argv[3]) : 6;
  SCOTCH_Num          n    = nf + nfree;
  SCOTCH_Num *        velotab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        parttab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num          i;
  int                 r;

  for (i = 0; i < n; i ++) {
    velotab[i] = 1;
    parttab[i] = -1;
  }
  for (i = 0; i < nf; i ++) {
    velotab[i] = w0;
    parttab[i] = 100 + i;
  }
  mkpath (&g, n, velotab, 1);
  SCOTCH_archInit  (&a);
  SCOTCH_archCmplt (&a, 1024);
  SCOTCH_stratInit (&s);
  r = SCOTCH_graphMapFixed (&g, &a, &s, parttab);
  printf ("ret=%d", r);
  for (i = 0; i < n; i ++)
    printf (" %ld", (long) parttab[i]);
  printf ("\n");
  return ((r != 0) ? 1 : 0);
}
