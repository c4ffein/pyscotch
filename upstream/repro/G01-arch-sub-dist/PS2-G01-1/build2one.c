/* Build a type-2 decomposition-defined architecture restricted to a single
** vertex of a graph (SCOTCH_archBuild2 with listnbr = 1), the vertex not
** being vertex 0; then save, free, and report. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"

int
main (
int                 argc,
char *              argv[])
{
  SCOTCH_Graph        grafdat;
  SCOTCH_Arch         archdat;
  SCOTCH_Num          listtab[1];
  FILE *              fileptr;
  int                 o;

  SCOTCH_errorProg (argv[0]);
  listtab[0] = (SCOTCH_Num) atol (argv[2]);
  if ((fileptr = fopen (argv[1], "r")) == NULL)
    return (2);
  SCOTCH_graphInit (&grafdat);
  if (SCOTCH_graphLoad (&grafdat, fileptr, 0, 0) != 0)
    return (2);
  fclose (fileptr);
  SCOTCH_archInit (&archdat);
  o = SCOTCH_archBuild2 (&archdat, &grafdat, 1, listtab);
  printf ("build2 ret=%d\n", o);
  if (o == 0) {
    printf ("name=%s size=%ld\n", SCOTCH_archName (&archdat), (long) SCOTCH_archSize (&archdat));
    SCOTCH_archSave (&archdat, stdout);
    SCOTCH_archExit (&archdat);
  }
  SCOTCH_graphExit (&grafdat);
  return (o);
}
