/* API-18 / PS-API-7: SCOTCH_dgraphMapView versus SCOTCH_graphMapView.
** Loads the same graph file as a Dgraph (on however many processes) and
** as a Graph (on process 0), maps the Dgraph on the given target, saves the
** distributed mapping to a temporary file, reloads it into the sequential
** mapping, then prints both views to stdout on process 0:
**   first the "M" lines of SCOTCH_graphMapView, then "---", then those of
**   SCOTCH_dgraphMapView. Every line present in both must be identical
**   (PartDiam exists only in the sequential view).
** Usage: mpirun -np N dview graph.grf target.tgt [strategy]
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <mpi.h>
#include "ptscotch.h"

int
main (int argc, char * argv[])
{
  SCOTCH_Dgraph   dgrfdat;
  SCOTCH_Dmapping dmapdat;
  SCOTCH_Graph    grafdat;
  SCOTCH_Mapping  mappdat;
  SCOTCH_Arch     archdat;
  SCOTCH_Strat    stradat;
  FILE *          stream;
  FILE *          mapstream;
  char            mapname[64];
  int             procnum;
  int             o = 0;

  MPI_Init (&argc, &argv);
  MPI_Comm_rank (MPI_COMM_WORLD, &procnum);
  if (argc < 3) {
    fprintf (stderr, "usage: %s graph target [strategy]\n", argv[0]);
    MPI_Abort (MPI_COMM_WORLD, 1);
  }

  SCOTCH_archInit (&archdat);
  stream = fopen (argv[2], "r");
  o |= SCOTCH_archLoad (&archdat, stream);
  fclose (stream);

  SCOTCH_dgraphInit (&dgrfdat, MPI_COMM_WORLD);
  stream = (procnum == 0) ? fopen (argv[1], "r") : NULL; /* Centralized graph file: only root process reads it */
  o |= SCOTCH_dgraphLoad (&dgrfdat, stream, -1, 0);
  if (stream != NULL)
    fclose (stream);
  o |= SCOTCH_dgraphCheck (&dgrfdat);

  SCOTCH_stratInit (&stradat);
  if (argc > 3)
    o |= SCOTCH_stratDgraphMap (&stradat, argv[3]);
  o |= SCOTCH_dgraphMapInit (&dgrfdat, &dmapdat, &archdat, NULL);
  o |= SCOTCH_dgraphMapCompute (&dgrfdat, &dmapdat, &stradat);
  if (o != 0) {
    fprintf (stderr, "distributed mapping failed\n");
    MPI_Abort (MPI_COMM_WORLD, 1);
  }

  sprintf (mapname, "dview_%d.map", (int) getpid ());
  mapstream = (procnum == 0) ? fopen (mapname, "w") : NULL;
  o |= SCOTCH_dgraphMapSave (&dgrfdat, &dmapdat, mapstream);
  if (mapstream != NULL)
    fclose (mapstream);

  if (procnum == 0) {
    SCOTCH_graphInit (&grafdat);
    stream = fopen (argv[1], "r");
    o |= SCOTCH_graphLoad (&grafdat, stream, -1, 0);
    fclose (stream);
    o |= SCOTCH_graphMapInit (&grafdat, &mappdat, &archdat, NULL);
    stream = fopen (mapname, "r");
    o |= SCOTCH_graphMapLoad (&grafdat, &mappdat, stream);
    fclose (stream);
    remove (mapname);
    o |= SCOTCH_graphMapView (&grafdat, &mappdat, stdout);
    printf ("---\n");
    fflush (stdout);
  }
  o |= SCOTCH_dgraphMapView (&dgrfdat, &dmapdat, (procnum == 0) ? stdout : NULL);
  if (procnum == 0) {
    SCOTCH_graphMapExit (&grafdat, &mappdat);
    SCOTCH_graphExit (&grafdat);
  }

  SCOTCH_dgraphMapExit (&dgrfdat, &dmapdat);
  SCOTCH_dgraphExit (&dgrfdat);
  SCOTCH_stratExit (&stradat);
  SCOTCH_archExit (&archdat);
  MPI_Finalize ();
  return (o ? EXIT_FAILURE : EXIT_SUCCESS);
}
