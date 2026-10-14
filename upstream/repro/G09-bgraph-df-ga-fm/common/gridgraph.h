/* Build an n x n 4-neighbour grid as a SCOTCH_Graph (base 0).
** veloval / edloval : vertex and edge loads (0 = no load array). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <scotch.h>

static int
gridBuild (SCOTCH_Graph * const grafptr, const SCOTCH_Num n, const SCOTCH_Num veloval, const SCOTCH_Num edloval)
{
  SCOTCH_Num   vertnbr = n * n;
  SCOTCH_Num * verttab = malloc ((vertnbr + 1) * sizeof (SCOTCH_Num));
  SCOTCH_Num * edgetab = malloc (4 * vertnbr * sizeof (SCOTCH_Num));
  SCOTCH_Num * velotab = (veloval != 0) ? malloc (vertnbr * sizeof (SCOTCH_Num)) : NULL;
  SCOTCH_Num * edlotab = (edloval != 0) ? malloc (4 * vertnbr * sizeof (SCOTCH_Num)) : NULL;
  SCOTCH_Num   edgenbr = 0, i, j;

  for (i = 0; i < n; i ++) {
    for (j = 0; j < n; j ++) {
      SCOTCH_Num v = i * n + j;
      verttab[v] = edgenbr;
      if (velotab != NULL) velotab[v] = veloval;
      if (i > 0)     edgetab[edgenbr ++] = v - n;
      if (j > 0)     edgetab[edgenbr ++] = v - 1;
      if (j < n - 1) edgetab[edgenbr ++] = v + 1;
      if (i < n - 1) edgetab[edgenbr ++] = v + n;
    }
  }
  verttab[vertnbr] = edgenbr;
  if (edlotab != NULL) for (i = 0; i < edgenbr; i ++) edlotab[i] = edloval;
  SCOTCH_graphInit (grafptr);
  return (SCOTCH_graphBuild (grafptr, 0, vertnbr, verttab, NULL, velotab, NULL, edgenbr, edgetab, edlotab));
}
