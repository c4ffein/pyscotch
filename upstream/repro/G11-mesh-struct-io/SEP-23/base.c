/* Internal-API harness: meshBase()/hmeshBase() round trip with loads and a distinct vehdtax. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "module.h"
#include "common.h"
#include "graph.h"
#include "mesh.h"
#include "hmesh.h"
#include "scotch.h"
static SCOTCH_Num verttab[7]  = { 1, 4, 7, 8, 10, 12, 13 };   /* 2 elements (1,2), 4 nodes (3..6), base 1 */
static SCOTCH_Num velotab[2]  = { 2, 3 };
static SCOTCH_Num vnlotab[4]  = { 1, 2, 3, 4 };
static SCOTCH_Num edgetab[12] = { 3, 4, 5,  4, 5, 6,  1,  1, 2,  1, 2,  2 };
int main (int argc, char * argv[])
{
  SCOTCH_Mesh meshdat; Mesh * meshptr; Hmesh hmshdat; Gnum vehdtab[2]; Gnum vertnum; int o;
  SCOTCH_meshInit (&meshdat);
  SCOTCH_meshBuild (&meshdat, 1, 3, 2, 4, verttab, NULL, velotab, vnlotab, NULL, 12, edgetab);
  meshptr = (Mesh *) &meshdat;
  printf ("check0=%d\n", meshCheck (meshptr));
  o = meshBase (meshptr, 0); printf ("meshBase->0 old=%d check=%d\n", (int) o, meshCheck (meshptr));
  o = meshBase (meshptr, 1); printf ("meshBase->1 old=%d check=%d\n", (int) o, meshCheck (meshptr));
  printf ("velotax[1..2]=%d %d vnlotax[3..6]=%d %d %d %d\n", (int) meshptr->velotax[1], (int) meshptr->velotax[2],
          (int) meshptr->vnlotax[3], (int) meshptr->vnlotax[4], (int) meshptr->vnlotax[5], (int) meshptr->vnlotax[6]);
  memset (&hmshdat, 0, sizeof (Hmesh)); hmshdat.m = *meshptr; hmshdat.vehdtax = hmshdat.m.vendtax;
  hmshdat.vnohnbr = hmshdat.m.vnodnbr; hmshdat.vnohnnd = hmshdat.m.vnodnnd; hmshdat.vnhlsum = hmshdat.m.vnlosum; hmshdat.enohnbr = hmshdat.m.edgenbr;
  printf ("hcheck0=%d\n", hmeshCheck (&hmshdat));
  o = hmeshBase (&hmshdat, 0); printf ("hmeshBase(alias)->0 old=%d check=%d alias=%d\n", (int) o, hmeshCheck (&hmshdat), hmshdat.vehdtax == hmshdat.m.vendtax);
  o = hmeshBase (&hmshdat, 1); printf ("hmeshBase(alias)->1 old=%d check=%d alias=%d\n", (int) o, hmeshCheck (&hmshdat), hmshdat.vehdtax == hmshdat.m.vendtax);
  for (vertnum = hmshdat.m.velmbas; vertnum < hmshdat.m.velmnnd; vertnum ++) vehdtab[vertnum - hmshdat.m.velmbas] = hmshdat.m.vendtax[vertnum];
  hmshdat.vehdtax = vehdtab - hmshdat.m.velmbas;
  printf ("hcheck1=%d\n", hmeshCheck (&hmshdat));
  o = hmeshBase (&hmshdat, 0); printf ("hmeshBase(distinct)->0 old=%d check=%d vehd=%d %d\n", (int) o, hmeshCheck (&hmshdat), (int) vehdtab[0], (int) vehdtab[1]);
  o = hmeshBase (&hmshdat, 1); printf ("hmeshBase(distinct)->1 old=%d check=%d vehd=%d %d\n", (int) o, hmeshCheck (&hmshdat), (int) vehdtab[0], (int) vehdtab[1]);
  return (0);
}
