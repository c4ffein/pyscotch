/* Exercise SCOTCH_contextOptionSetNum / SCOTCH_contextOptionParse return values and side effects */
#include <stdio.h>
#include <stdlib.h>
#include <scotch.h>

static
void
optsPrint (
SCOTCH_Context * const      contptr,
const char * const          lablstr)
{
  SCOTCH_Num          deteval;
  SCOTCH_Num          rafival;

  SCOTCH_contextOptionGetNum (contptr, SCOTCH_OPTIONNUMDETERMINISTIC, &deteval);
  SCOTCH_contextOptionGetNum (contptr, SCOTCH_OPTIONNUMRANDOMFIXEDSEED, &rafival);
  printf ("%-28s deterministic=%ld fixedseed=%ld\n", lablstr, (long) deteval, (long) rafival);
}

int
main (
int                 argc,
char *              argv[])
{
  SCOTCH_Context *    contptr;
  int                 o;

  contptr = SCOTCH_contextAlloc ();
  SCOTCH_contextInit (contptr);
  optsPrint (contptr, "initial");
  o = SCOTCH_contextOptionSetNum (contptr, SCOTCH_OPTIONNUMDETERMINISTIC, 1);
  printf ("SetNum (DETERMINISTIC, 1) = %d\n", o);
  optsPrint (contptr, "after SetNum");
  o = SCOTCH_contextOptionSetNum (contptr, SCOTCH_OPTIONNUMDETERMINISTIC, 5);
  printf ("SetNum (DETERMINISTIC, 5) = %d\n", o);
  o = SCOTCH_contextOptionSetNum (contptr, 7, 1);
  printf ("SetNum (7, 1) = %d (expect 1)\n", o);
  SCOTCH_contextExit (contptr);

  SCOTCH_contextInit (contptr);
  o = SCOTCH_contextOptionParse (contptr, "d");
  printf ("Parse (\"d\") = %d\n", o);
  optsPrint (contptr, "after Parse d");
  o = SCOTCH_contextOptionParse (contptr, "x");
  printf ("Parse (\"x\") = %d (expect 1)\n", o);
  o = SCOTCH_contextOptionParse (contptr, "d,r");
  printf ("Parse (\"d,r\") = %d\n", o);
  optsPrint (contptr, "after Parse d,r");
  o = SCOTCH_contextOptionParse (contptr, "u");
  printf ("Parse (\"u\") = %d\n", o);
  optsPrint (contptr, "after Parse u");
  SCOTCH_contextExit (contptr);
  free (contptr);
  return (0);
}
