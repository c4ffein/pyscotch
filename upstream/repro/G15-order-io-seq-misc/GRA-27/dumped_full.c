#include "module.h"
#include "common.h"
#include "graph.h"
Gnum myverttab_x[] = {
  0, 2, 4, 6
};

Gnum myedgetab_x[] = {
  1, 2, 0, 2, 0, 1
};

Gnum myedlotab_x[] = {
  5, 7, 5, 9, 7, 9
};

void
myGraphBuild_x (
Graph *               grafptr)
{
  graphInit (grafptr);
  grafptr->baseval = 0;
  grafptr->vertnbr = 3;
  grafptr->vertnnd = 3;
  grafptr->verttax = myverttab_x - 0;
  grafptr->vendtax = grafptr->verttax + 1;
  grafptr->velosum = 3;
  grafptr->edgenbr = 6;
  grafptr->edgetax = myedgetab_x - 0;
  grafptr->edlotax = myedlotab_x - 0;
  grafptr->edlosum = 42;
  grafptr->degrmax = 2;
}
