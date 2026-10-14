/* Load one target architecture file through the public API and report. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (
int                 argc,
char *              argv[])
{
  SCOTCH_Arch         archdat;
  FILE *              fileptr;
  int                 o;

  SCOTCH_errorProg (argv[0]);
  if ((fileptr = fopen (argv[1], "r")) == NULL) {
    fprintf (stderr, "cannot open %s\n", argv[1]);
    return (2);
  }
  SCOTCH_archInit (&archdat);
  o = SCOTCH_archLoad (&archdat, fileptr);
  fclose (fileptr);
  printf ("load ret=%d\n", o);
  if (o == 0)
    printf ("name=%s size=%ld\n", SCOTCH_archName (&archdat), (long) SCOTCH_archSize (&archdat));
  SCOTCH_archExit (&archdat);                       /* Always exit, as test_scotch_arch.c does on success */
  return ((o == 0) ? 0 : 1);
}
