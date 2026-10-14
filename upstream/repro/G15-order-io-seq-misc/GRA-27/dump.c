/* GRA-27 harness: call the internal graphDump() on a 3-vertex graph with
** edge loads and write the generated C code to stdout; the output is then
** compiled with gcc against the libscotch internal headers.
*/
#include <stdio.h>
#include <stdlib.h>
#include "module.h"
#include "common.h"
#include "graph.h"
#include "graph_dump.h"

int
main (int argc, char * argv[])
{
  Graph               grafdat;
  static Gnum         verttab[4] = { 0, 2, 4, 6 };
  static Gnum         edgetab[6] = { 1, 2, 0, 2, 0, 1 };
  static Gnum         edlotab[6] = { 5, 7, 5, 9, 7, 9 };

  graphInit (&grafdat);                           /* Fill graph structure by hand (no internal build routine) */
  grafdat.baseval = 0;
  grafdat.vertnbr = 3;
  grafdat.vertnnd = 3;
  grafdat.verttax = verttab;
  grafdat.vendtax = verttab + 1;
  grafdat.velosum = 3;
  grafdat.edgenbr = 6;
  grafdat.edgetax = edgetab;
  grafdat.edlotax = edlotab;
  grafdat.edlosum = 42;
  grafdat.degrmax = 2;
  if (graphCheck (&grafdat) != 0)
    return (3);
  if (graphDump (&grafdat, "my", "_x", stdout) != 0)
    return (2);
  grafdat.flagval = GRAPHNONE;                    /* Arrays are static */
  graphExit (&grafdat);
  return (0);
}
