/* GRA-05: SCOTCH_graphRemap of a 32x32 grid from an old partition into
** oldnbr vertical strips onto cmplt(newnbr).
** usage: gra05 oldnbr newnbr [strategy] */
#include "../common/mk.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        g;
  SCOTCH_Arch         a;
  SCOTCH_Strat        s;
  int                 w = 32;
  int                 kold = atoi (argv[1]);
  int                 knew = atoi (argv[2]);
  SCOTCH_Num          n = (SCOTCH_Num) w * w;
  SCOTCH_Num *        parotab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num *        parttab = malloc (n * sizeof (SCOTCH_Num));
  SCOTCH_Num          i;
  int                 r;

  mkgrid (&g, w, w, NULL);
  for (i = 0; i < n; i ++)
    parotab[i] = (i % w) * kold / w;
  SCOTCH_archInit  (&a);
  SCOTCH_archCmplt (&a, knew);
  SCOTCH_stratInit (&s);
  if ((argc > 3) && (SCOTCH_stratGraphMap (&s, argv[3]) != 0)) {
    fprintf (stderr, "invalid strategy\n");
    return (2);
  }
  r = SCOTCH_graphRemap (&g, &a, parotab, 0.1, NULL, &s, parttab);
  printf ("ret=%d\n", r);
  return ((r != 0) ? 1 : 0);
}
