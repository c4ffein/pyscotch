#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[]) {
  SCOTCH_Graph grafdat; SCOTCH_Arch archdat; SCOTCH_Strat stradat; SCOTCH_Graph indgrafdat;
  SCOTCH_Num verttab[5] = { 0, 1, 3, 5, 6 }; SCOTCH_Num edgetab[6] = { 1, 0, 2, 1, 3, 2 };
  SCOTCH_Num badlist[2] = { 0, 99 }; SCOTCH_Num duplist[3] = { 1, 1, 2 };
  int o;
  SCOTCH_graphInit (&grafdat);
  SCOTCH_graphBuild (&grafdat, 0, 4, verttab, NULL, NULL, NULL, 6, edgetab, NULL);
  SCOTCH_stratInit (&stradat);
  SCOTCH_archInit (&archdat);
  if (argc > 1 && argv[1][0] == 'd') { o = SCOTCH_archBuild0 (&archdat, &grafdat, 3, duplist, &stradat); printf ("archBuild0 dup list: %d\n", o); SCOTCH_archSave (&archdat, stdout); }
  else if (argc > 1 && argv[1][0] == 'i') { SCOTCH_graphInit (&indgrafdat); o = SCOTCH_graphInduceList (&grafdat, 2, badlist, &indgrafdat); printf ("graphInduceList bad list: %d\n", o); }
  else { o = SCOTCH_archBuild0 (&archdat, &grafdat, 2, badlist, &stradat); printf ("archBuild0 bad list: %d\n", o); }
  return (0);
}
