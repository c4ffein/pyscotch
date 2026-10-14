/* Drive archCmpltMatchInit/Mate directly (internal symbols, SCOTCH_RENAME build)
** and print, for each coarsening level, the number of coarse vertices, the
** pass number stored for the next level, the fine vertices left single, and
** the number of fine vertices covered by the multinode array. */
#include <stdio.h>
#include <stdlib.h>
#include "module.h"
#include "common.h"
#include "arch.h"
#include "arch_cmplt.h"

int
main (
int                 argc,
char *              argv[])
{
  ArchCmplt           archdat;
  ArchCmpltMatch      matcdat;
  ArchCoarsenMulti *  multtab;
  Anum                coarvertnbr;
  Anum                finevertnbr;
  int                 levlnum;
  int                 o;

  archdat.termnbr = (Anum) atol (argv[1]);
  if (archCmpltMatchInit (&matcdat, &archdat) != 0)
    return (2);

  o = 0;
  for (levlnum = 0, finevertnbr = archdat.termnbr; finevertnbr > 1; levlnum ++, finevertnbr = coarvertnbr) {
    Anum                coarvertnum;
    Anum                covered;

    if ((coarvertnbr = archCmpltMatchMate (&matcdat, &multtab)) < 0) {
      printf ("level %d: error\n", levlnum);
      o = 1;
      break;
    }
    printf ("level %d: fine=%ld coarse=%ld nextpass=%ld single:", levlnum, (long) finevertnbr, (long) coarvertnbr, (long) matcdat.passnum);
    for (coarvertnum = covered = 0; coarvertnum < coarvertnbr; coarvertnum ++) {
      if (multtab[coarvertnum].vertnum[0] == multtab[coarvertnum].vertnum[1]) {
        printf (" %ld", (long) multtab[coarvertnum].vertnum[0]);
        covered ++;
      }
      else
        covered += 2;
    }
    printf (" covered=%ld%s\n", (long) covered, (covered != finevertnbr) ? " MISMATCH" : "");
    if (covered != finevertnbr)
      o = 1;
  }
  archCmpltMatchExit (&matcdat);
  return (o);
}
