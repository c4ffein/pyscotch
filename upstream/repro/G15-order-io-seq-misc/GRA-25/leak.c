/* GRA-25 harness: order a graph or a mesh with a strategy whose compressed
** ordering fails after the column block tree has been built, then scrub the
** stack so that LeakSanitizer does not see stale pointers to the leaked
** column block tree.
** usage: leak g <graph.grf> <strategy>   |   leak m <mesh.msh> <strategy>
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"

static int
orderGraph (const char * const fileptr, const char * const strastr)
{
  SCOTCH_Graph        grafdat;
  SCOTCH_Strat        stradat;
  SCOTCH_Num          vertnbr;
  SCOTCH_Num *        peritab;
  FILE *              stream;
  int                 o;

  SCOTCH_graphInit (&grafdat);
  if ((stream = fopen (fileptr, "r")) == NULL) return (3);
  if (SCOTCH_graphLoad (&grafdat, stream, -1, 0) != 0) return (3);
  fclose (stream);
  SCOTCH_graphData (&grafdat, NULL, &vertnbr, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
  peritab = malloc (vertnbr * sizeof (SCOTCH_Num));
  SCOTCH_stratInit (&stradat);
  if (SCOTCH_stratGraphOrder (&stradat, strastr) != 0) return (3);
  o = SCOTCH_graphOrder (&grafdat, &stradat, NULL, peritab, NULL, NULL, NULL);
  SCOTCH_stratExit (&stradat);
  SCOTCH_graphExit (&grafdat);
  free (peritab);
  return (o);
}

static int
orderMesh (const char * const fileptr, const char * const strastr)
{
  SCOTCH_Mesh         meshdat;
  SCOTCH_Strat        stradat;
  SCOTCH_Num          vnodnbr;
  SCOTCH_Num *        peritab;
  FILE *              stream;
  int                 o;

  SCOTCH_meshInit (&meshdat);
  if ((stream = fopen (fileptr, "r")) == NULL) return (3);
  if (SCOTCH_meshLoad (&meshdat, stream, -1) != 0) return (3);
  fclose (stream);
  SCOTCH_meshData (&meshdat, NULL, NULL, NULL, &vnodnbr, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
  peritab = malloc (vnodnbr * sizeof (SCOTCH_Num));
  SCOTCH_stratInit (&stradat);
  if (SCOTCH_stratMeshOrder (&stradat, strastr) != 0) return (3);
  o = SCOTCH_meshOrder (&meshdat, &stradat, NULL, peritab, NULL, NULL, NULL);
  SCOTCH_stratExit (&stradat);
  SCOTCH_meshExit (&meshdat);
  free (peritab);
  return (o);
}

static void
scrub (int depth)
{
  volatile char       buftab[65536];

  memset ((char *) buftab, 0, sizeof (buftab));
  if (depth > 0)
    scrub (depth - 1);
}

int
main (int argc, char * argv[])
{
  int                 o;

  SCOTCH_errorProg (argv[0]);
  o = (argv[1][0] == 'g') ? orderGraph (argv[2], argv[3]) : orderMesh (argv[2], argv[3]);
  printf ("order ret=%d\n", o);
  scrub (8);                                      /* Overwrite stale stack frames before leak check at exit */
  return (0);
}
