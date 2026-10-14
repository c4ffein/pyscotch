/* Internal-API harness: hmeshExit() on a nodes-first halo mesh whose vehdtax aliases m.vendtax (distinct vendtab, MESHFREEVEND). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "module.h"
#include "common.h"
#include "graph.h"
#include "mesh.h"
#include "hmesh.h"
int main (int argc, char * argv[])
{
  Hmesh h; Gnum * verttab, * vendtab, * edgetab;
  static const Gnum vt[6] = { 0, 1, 3, 4, 6, 9 }, ve[6] = { 1, 3, 4, 6, 9, 12 }, ed[12] = { 4,  4, 5,  5,  4, 5,  0, 1, 3,  1, 2, 3 };
  verttab = memAlloc (6 * sizeof (Gnum)); vendtab = memAlloc (6 * sizeof (Gnum)); edgetab = memAlloc (12 * sizeof (Gnum));
  memCpy (verttab, vt, sizeof (vt)); memCpy (vendtab, ve, sizeof (ve)); memCpy (edgetab, ed, sizeof (ed));
  memset (&h, 0, sizeof (Hmesh));
  h.m.flagval = MESHFREEVERT | MESHFREEVEND | MESHFREEEDGE; h.m.baseval = 0; h.m.velmnbr = 2; h.m.velmbas = 4; h.m.velmnnd = 6;
  h.m.vnodnbr = 4; h.m.vnodbas = 0; h.m.vnodnnd = 4; h.m.verttax = verttab; h.m.vendtax = vendtab;
  h.m.velosum = 2; h.m.vnlosum = 4; h.m.edgenbr = 12; h.m.edgetax = edgetab; h.m.degrmax = 3;
  h.vehdtax = h.m.vendtax; h.vnohnbr = 4; h.vnohnnd = 4; h.vnhlsum = 4; h.enohnbr = 12; /* No halo: vehdtax aliases vendtax */
  printf ("hmeshCheck=%d\n", hmeshCheck (&h));
  hmeshExit (&h);
  printf ("hmeshExit done\n");
  return (0);
}
