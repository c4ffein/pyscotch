/* SCOTCH_archCmpltw with a zero weight: archCmpltwArchBuild2 frees the caller's array instead of its own */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[]) {
  SCOTCH_Arch a; SCOTCH_Num * velotab; int r;
  SCOTCH_errorProg (argv[0]);
  velotab = malloc (4 * sizeof (SCOTCH_Num));
  velotab[0] = 1; velotab[1] = 0; velotab[2] = 1; velotab[3] = 1;
  SCOTCH_archInit (&a);
  r = SCOTCH_archCmpltw (&a, 4, velotab);
  printf ("archCmpltw r=%d\n", r);
  free (velotab);                                 /* Caller still owns its array */
  SCOTCH_archExit (&a);
  printf ("exit ok\n");
  return (0);
}
