/* COR-15: load a target architecture file and print its size. */
#include <stdio.h>
#include <stdlib.h>
#include <scotch.h>

int
main (int argc, char * argv[])
{
  SCOTCH_Arch         archdat;
  FILE *              stream;
  int                 o;

  SCOTCH_archInit (&archdat);
  if ((stream = fopen (argv[1], "r")) == NULL) {
    fprintf (stderr, "cannot open %s\n", argv[1]);
    return (2);
  }
  o = SCOTCH_archLoad (&archdat, stream);
  fclose (stream);
  printf ("archLoad ret=%d\n", o);
  if (o == 0)
    printf ("archSize=%lld name=%s\n", (long long) SCOTCH_archSize (&archdat), SCOTCH_archName (&archdat));
  SCOTCH_archExit (&archdat);
  return (0);
}
