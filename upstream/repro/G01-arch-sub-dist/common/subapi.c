/* Call SCOTCH_archSub() with an invalid terminal list (duplicate vertex
** numbers) on a complete graph architecture; expected: non-zero return,
** no sanitizer report, no leak. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (
int                 argc,
char *              argv[])
{
  SCOTCH_Arch         orgarchdat;
  SCOTCH_Arch         subarchdat;
  SCOTCH_Num          vnumtab[2];
  int                 o;

  SCOTCH_errorProg (argv[0]);
  vnumtab[0] = (SCOTCH_Num) atol (argv[1]);
  vnumtab[1] = (SCOTCH_Num) atol (argv[2]);
  SCOTCH_archInit (&orgarchdat);
  SCOTCH_archCmplt (&orgarchdat, 4);
  SCOTCH_archInit (&subarchdat);
  o = SCOTCH_archSub (&subarchdat, &orgarchdat, 2, vnumtab);
  printf ("archSub ret=%d\n", o);
  if (o == 0)
    SCOTCH_archExit (&subarchdat);
  SCOTCH_archExit (&orgarchdat);
  return (o);
}
