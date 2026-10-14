/* dtest: PT-Scotch driver for the G23 reproducers.
**
** usage: dtest <graph> <base|-1> order|map|part <strategy|""> <nparts> <save> <outfile|->
**   save (order): o = SCOTCH_dgraphOrderSave, t = SaveTree, m = SaveMap, b = SaveBlock, n = none
**   save (map/part): s = SCOTCH_dgraphMapSave (map only), n = none
** The G18 LD_PRELOAD fault injector (fishim.so) is armed just before the compute call.
** Link with libptscotcherr (non-exiting errorPrint) so that collective misbehaviour shows as hangs.
*/

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "ptscotch.h"

int
main (
int                         argc,
char *                      argv[])
{
  int                 procglbnbr;
  int                 proclocnum;
  SCOTCH_Dgraph       grafdat;
  SCOTCH_Strat        stradat;
  SCOTCH_Num          baseval;
  SCOTCH_Num          partnbr;
  FILE *              fileptr;
  FILE *              outptr;
  const char *        modeptr;
  const char *        straptr;
  char                saveval;
  volatile long *     armdptr;
  int                 o;

  if (argc != 8) {
    fprintf (stderr, "usage: dtest graph base order|map|part strategy nparts save outfile\n");
    return (1);
  }

  {                                               /* PT-Scotch threads (fold-dup coarsening) perform MPI calls concurrently */
    int                 thrdprolvl;

    if ((MPI_Init_thread (&argc, &argv, MPI_THREAD_MULTIPLE, &thrdprolvl) != MPI_SUCCESS) || (thrdprolvl < MPI_THREAD_MULTIPLE)) {
      fprintf (stderr, "MPI_THREAD_MULTIPLE not available\n");
      return (1);
    }
  }
  MPI_Comm_size (MPI_COMM_WORLD, &procglbnbr);
  MPI_Comm_rank (MPI_COMM_WORLD, &proclocnum);

  baseval = (SCOTCH_Num) atol (argv[2]);
  modeptr = argv[3];
  straptr = argv[4];
  partnbr = (SCOTCH_Num) atol (argv[5]);
  saveval = argv[6][0];

  if (SCOTCH_dgraphInit (&grafdat, MPI_COMM_WORLD) != 0) {
    fprintf (stderr, "rank %d: dgraphInit failed\n", proclocnum);
    MPI_Abort (MPI_COMM_WORLD, 1);
  }
  fileptr = (proclocnum == 0) ? fopen (argv[1], "r") : NULL;
  if ((proclocnum == 0) && (fileptr == NULL)) {
    fprintf (stderr, "cannot open %s\n", argv[1]);
    MPI_Abort (MPI_COMM_WORLD, 1);
  }
  if (SCOTCH_dgraphLoad (&grafdat, fileptr, baseval, 0) != 0) {
    fprintf (stderr, "rank %d: dgraphLoad failed\n", proclocnum);
    MPI_Abort (MPI_COMM_WORLD, 1);
  }
  if (fileptr != NULL)
    fclose (fileptr);

  SCOTCH_stratInit (&stradat);
  if (straptr[0] != '\0') {
    o = (modeptr[0] == 'o') ? SCOTCH_stratDgraphOrder (&stradat, straptr) : SCOTCH_stratDgraphMap (&stradat, straptr);
    if (o != 0) {
      fprintf (stderr, "rank %d: strategy parsing failed\n", proclocnum);
      MPI_Abort (MPI_COMM_WORLD, 1);
    }
  }

  outptr = ((proclocnum == 0) && (strcmp (argv[7], "-") != 0)) ? fopen (argv[7], "w") : NULL;

  armdptr = (volatile long *) dlsym (RTLD_DEFAULT, "fi_armed"); /* Arm the fault injector if preloaded */
  if (armdptr != NULL)
    *armdptr = 1;

  if (modeptr[0] == 'o') {
    SCOTCH_Dordering    ordedat;
    SCOTCH_Num          cblknbr;

    if (SCOTCH_dgraphOrderInit (&grafdat, &ordedat) != 0) {
      fprintf (stderr, "rank %d: dgraphOrderInit failed\n", proclocnum);
      MPI_Abort (MPI_COMM_WORLD, 1);
    }
    o = SCOTCH_dgraphOrderCompute (&grafdat, &ordedat, &stradat);
    printf ("rank %d: OrderCompute rc=%d\n", proclocnum, o);
    fflush (stdout);
    if (o == 0) {
      cblknbr = SCOTCH_dgraphOrderCblkDist (&grafdat, &ordedat);
      printf ("rank %d: CblkDist=%ld\n", proclocnum, (long) cblknbr);
      switch (saveval) {
        case 'o' :
          o = SCOTCH_dgraphOrderSave (&grafdat, &ordedat, outptr);
          break;
        case 't' :
          o = SCOTCH_dgraphOrderSaveTree (&grafdat, &ordedat, outptr);
          break;
        case 'm' :
          o = SCOTCH_dgraphOrderSaveMap (&grafdat, &ordedat, outptr);
          break;
        case 'b' :
          o = SCOTCH_dgraphOrderSaveBlock (&grafdat, &ordedat, outptr);
          break;
        default :
          o = 0;
          saveval = 'n';
      }
      if (saveval != 'n')
        printf ("rank %d: OrderSave(%c) rc=%d\n", proclocnum, saveval, o);
      fflush (stdout);
    }
    SCOTCH_dgraphOrderExit (&grafdat, &ordedat);
  }
  else {
    SCOTCH_Num          vertlocnbr;
    SCOTCH_Num *        parttab;

    SCOTCH_dgraphSize (&grafdat, NULL, &vertlocnbr, NULL, NULL);
    if ((parttab = malloc ((vertlocnbr + 1) * sizeof (SCOTCH_Num))) == NULL)
      MPI_Abort (MPI_COMM_WORLD, 1);
    if (modeptr[0] == 'p') {
      o = SCOTCH_dgraphPart (&grafdat, partnbr, &stradat, parttab);
      printf ("rank %d: Part rc=%d\n", proclocnum, o);
    }
    else {
      SCOTCH_Arch         archdat;
      SCOTCH_Dmapping     mappdat;

      SCOTCH_archInit  (&archdat);
      SCOTCH_archCmplt (&archdat, partnbr);
      if (saveval == 's') {                       /* Map and save, as dgmap does: no user part array, so no dmapTerm() */
        if (SCOTCH_dgraphMapInit (&grafdat, &mappdat, &archdat, NULL) != 0)
          MPI_Abort (MPI_COMM_WORLD, 1);
        o = SCOTCH_dgraphMapCompute (&grafdat, &mappdat, &stradat);
        printf ("rank %d: MapCompute rc=%d\n", proclocnum, o);
        fflush (stdout);
        o = SCOTCH_dgraphMapSave (&grafdat, &mappdat, outptr);
        printf ("rank %d: MapSave rc=%d\n", proclocnum, o);
        SCOTCH_dgraphMapExit (&grafdat, &mappdat);
      }
      else {
        o = SCOTCH_dgraphMap (&grafdat, &archdat, &stradat, parttab);
        printf ("rank %d: Map rc=%d\n", proclocnum, o);
      }
      SCOTCH_archExit (&archdat);
    }
    fflush (stdout);
    free (parttab);
  }

  if (armdptr != NULL)
    *armdptr = 0;

  if (outptr != NULL)
    fclose (outptr);
  SCOTCH_stratExit  (&stradat);
  SCOTCH_dgraphExit (&grafdat);
  MPI_Finalize ();

  return (0);
}
