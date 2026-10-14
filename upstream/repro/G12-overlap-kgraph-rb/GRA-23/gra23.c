/* GRA-23 (a): SCOTCH_graphRemap with an old partition containing an invalid
** terminal number (argv[1], e.g. 100) on cmplt(4): mapBuild3() stores an
** uninitialised domain and the call returns 0.
** usage: gra23 termnum */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Arch         a;
  SCOTCH_Strat        s;
  SCOTCH_Num          n = 256;
  SCOTCH_Num *        parotab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        parttab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num          i;
  int                 r;

  mkgrid (&g, 16, 16, NULL);
  for (i = 0; i < n; i ++)
    parotab[i] = i % 4;
  parotab[7] = atol (argv[1]);
  SCOTCH_archInit  (&a);
  SCOTCH_archCmplt (&a, 4);
  SCOTCH_stratInit (&s);
  r = SCOTCH_graphRemap (&g, &a, parotab, 0.1, NULL, &s, parttab);
  printf ("ret=%d new[7]=%ld\n", r, (long) parttab[7]);
  return (0);
}
