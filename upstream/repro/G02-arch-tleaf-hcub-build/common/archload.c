/* Load one target architecture from the string given as argv[1], print its size, then exit it */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"
int main (int argc, char * argv[]) {
  SCOTCH_Arch a; FILE * f; int r;
  SCOTCH_errorProg (argv[0]);
  f = tmpfile (); fputs (argv[1], f); fputc ('\n', f); rewind (f);
  SCOTCH_archInit (&a);
  r = SCOTCH_archLoad (&a, f); fclose (f);
  printf ("load ret=%d\n", r);
  if (r == 0) printf ("name=%s size=%ld\n", SCOTCH_archName (&a), (long) SCOTCH_archSize (&a));
  SCOTCH_archExit (&a);
  return (0);
}
