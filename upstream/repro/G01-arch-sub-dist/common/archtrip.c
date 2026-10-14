/* Load a target architecture file, save it to a second file, reload it from
** there, and report the sizes seen at each step. */
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
  if ((fileptr = fopen (argv[1], "r")) == NULL)
    return (2);
  SCOTCH_archInit (&archdat);
  o = SCOTCH_archLoad (&archdat, fileptr);
  fclose (fileptr);
  printf ("load ret=%d\n", o);
  if (o != 0) {
    SCOTCH_archExit (&archdat);
    return (1);
  }
  printf ("name=%s size=%ld var=%d\n", SCOTCH_archName (&archdat), (long) SCOTCH_archSize (&archdat), SCOTCH_archVar (&archdat));
  if ((fileptr = fopen (argv[2], "w")) == NULL)
    return (2);
  o = SCOTCH_archSave (&archdat, fileptr);
  fclose (fileptr);
  printf ("save ret=%d\n", o);
  SCOTCH_archExit (&archdat);

  if ((fileptr = fopen (argv[2], "r")) == NULL)
    return (2);
  SCOTCH_archInit (&archdat);
  o = SCOTCH_archLoad (&archdat, fileptr);
  fclose (fileptr);
  printf ("reload ret=%d\n", o);
  if (o == 0)
    printf ("name=%s size=%ld var=%d\n", SCOTCH_archName (&archdat), (long) SCOTCH_archSize (&archdat), SCOTCH_archVar (&archdat));
  SCOTCH_archExit (&archdat);
  return (o);
}
