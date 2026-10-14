/* dmaptest: internal-API driver for dmapSave() validation (DMO-15, null part arrays).
**
** usage: dmaptest <graph> <mode>
**   mode c : complete mapping (one fragment per process, all local vertices to domain 0)
**   mode x : over-complete mapping (the root process adds one extra vertex to its fragment)
**   mode n : complete mapping whose root fragment has no part array
** Each process prints the return value of dmapSave(); the root writes the mapping to stdout.
** Compile with the libscotch internal headers (see README); link with libptscotcherr.
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "module.h"
#include "common.h"
#include "arch.h"
#include "arch_cmplt.h"
#include "dgraph.h"
#include "dmapping.h"
#include "ptscotch.h"

int
main (
int                         argc,
char *                      argv[])
{
  Dgraph              grafdat;
  Arch                archdat;
  Dmapping            mappdat;
  DmappingFrag *      fragptr;
  FILE *              fileptr;
  int                 proclocnum;
  Gnum                vertlocnbr;
  Gnum                vertnum;
  Gnum                vertadj;
  char                modeval;
  int                 o;

  if (argc != 3) {
    fprintf (stderr, "usage: dmaptest graph c|x|n\n");
    return (1);
  }
  modeval = argv[2][0];

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &proclocnum);

  dgraphInit (&grafdat, MPI_COMM_WORLD);
  fileptr = (proclocnum == 0) ? fopen (argv[1], "r") : NULL;
  if (dgraphLoad (&grafdat, fileptr, -1, 0) != 0) {
    fprintf (stderr, "rank %d: cannot load graph\n", proclocnum);
    MPI_Abort (MPI_COMM_WORLD, 1);
  }
  if (fileptr != NULL)
    fclose (fileptr);

  archInit  (&archdat);
  SCOTCH_archCmplt ((SCOTCH_Arch *) &archdat, 4); /* Four-part complete graph target */
  dmapInit  (&mappdat, &archdat);

  vertlocnbr = grafdat.vertlocnbr;
  if ((modeval == 'x') && (proclocnum == 0))      /* Root process claims one vertex too many */
    vertlocnbr ++;

  fragptr = memAlloc (sizeof (DmappingFrag));
  fragptr->vertnbr = vertlocnbr;
  fragptr->vnumtab = memAlloc (vertlocnbr * sizeof (Gnum));
  fragptr->parttab = ((modeval == 'n') && (proclocnum == 0)) ? NULL : memAlloc (vertlocnbr * sizeof (Anum));
  fragptr->domnnbr = 1;
  fragptr->domntab = memAlloc (sizeof (ArchDom));
  archDomFrst (&archdat, &fragptr->domntab[0]);
  vertadj = grafdat.procvrttab[proclocnum];
  for (vertnum = 0; vertnum < vertlocnbr; vertnum ++) {
    fragptr->vnumtab[vertnum] = vertadj + (vertnum % grafdat.vertlocnbr); /* Keep indices in range */
    if (fragptr->parttab != NULL)
      fragptr->parttab[vertnum] = 0;
  }
  dmapAdd (&mappdat, fragptr);

  o = dmapSave (&mappdat, &grafdat, (proclocnum == 0) ? stdout : NULL);
  fflush (stdout);
  fprintf (stderr, "rank %d: dmapSave rc=%d\n", proclocnum, o);

  if (fragptr->parttab == NULL)                   /* dmapExit() frees fragment arrays */
    fragptr->parttab = memAlloc (sizeof (Anum));
  dmapExit   (&mappdat);
  archExit   (&archdat);
  dgraphExit (&grafdat);
  MPI_Finalize ();

  return (0);
}
