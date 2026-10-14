/* PS2-G25-1: SCOTCH_archCmpltw() frees the caller's weight array when a weight is not positive. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[])
{
  SCOTCH_Arch archdat;
  SCOTCH_Num * velotab = malloc (3 * sizeof (SCOTCH_Num));
  int r;
  setvbuf (stdout, NULL, _IONBF, 0);
  velotab[0] = 2; velotab[1] = 0; velotab[2] = 3;  /* One null weight: rejected by archCmpltwArchBuild2() */
  SCOTCH_archInit (&archdat);
  r = SCOTCH_archCmpltw (&archdat, 3, velotab);
  printf ("SCOTCH_archCmpltw returned %d (expected non-zero)\n", r);
  SCOTCH_archExit (&archdat);
  free (velotab);                                 /* Pristine 7.0.17: double free, velotab was freed by the library */
  printf ("caller freed its own array: OK\n");
  return 0;
}
