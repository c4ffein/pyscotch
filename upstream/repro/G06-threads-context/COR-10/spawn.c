/* Spawn a thread context of THRDNBR threads (argv[1]) through the public API, then destroy it */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sched.h>
#include <scotch.h>

int
main (
int                 argc,
char *              argv[])
{
  SCOTCH_Context *    contptr;
  int                 thrdnbr;
  int                 o;

  thrdnbr = (argc > 1) ? atoi (argv[1]) : 4;
  contptr = SCOTCH_contextAlloc ();
  if (SCOTCH_contextInit (contptr) != 0) {
    printf ("contextInit failed\n");
    return (1);
  }
  o = SCOTCH_contextThreadSpawn (contptr, thrdnbr, NULL);
  printf ("spawn (%d) returned %d\n", thrdnbr, o);
  fflush (stdout);
  SCOTCH_contextExit (contptr);
  free (contptr);
  printf ("exit done\n");
  return (0);
}
