/* Internal-API harness: hmeshMesh() on a nodes-first halo mesh (the branch fixed by f36ab36). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "module.h"
#include "common.h"
#include "graph.h"
#include "mesh.h"
#include "hmesh.h"
/* Nodes 0..3 (3 is halo), elements 4,5, base 0. Element adjacencies list non-halo nodes first. */
static Gnum verttab[7]  = { 0, 1, 3, 4, 6, 9, 12 };
static Gnum edgetab[12] = { 4,  4, 5,  5,  4, 5,  0, 1, 3,  1, 2, 3 };
static Gnum vehdtab[2]  = { 8, 11 };
int main (int argc, char * argv[])
{
  Hmesh h; Mesh m; int o;
  memset (&h, 0, sizeof (Hmesh));
  h.m.flagval = MESHNONE; h.m.baseval = 0; h.m.velmnbr = 2; h.m.velmbas = 4; h.m.velmnnd = 6; h.m.veisnbr = 0;
  h.m.vnodnbr = 4; h.m.vnodbas = 0; h.m.vnodnnd = 4; h.m.verttax = verttab; h.m.vendtax = verttab + 1;
  h.m.velosum = 2; h.m.vnlosum = 4; h.m.edgenbr = 12; h.m.edgetax = edgetab; h.m.degrmax = 3;
  h.vehdtax = vehdtab - 4; h.veihnbr = 0; h.vnohnbr = 3; h.vnohnnd = 3; h.vnhlsum = 3; h.enohnbr = 8;
  printf ("hmeshCheck=%d\n", hmeshCheck (&h));
  o = hmeshMesh (&h, &m);
  printf ("hmeshMesh=%d meshCheck=%d velmnbr=%d velmbas=%d vnodnbr=%d edgenbr=%d\n", o, (o == 0) ? meshCheck (&m) : -1,
          (int) m.velmnbr, (int) m.velmbas, (int) m.vnodnbr, (int) m.edgenbr);
  if (o == 0) meshExit (&m);
  return (0);
}
