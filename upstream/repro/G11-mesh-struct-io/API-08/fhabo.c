/* Call the Fortran entry of the Harwell-Boeing mesh loader (passes NULL tag). usage: fhabo file */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include "scotch.h"
void scotchfmeshgeomloadhabo_ (SCOTCH_Mesh *, SCOTCH_Geom *, const int *, const int *, const char *, int *, int);
int main (int argc, char * argv[])
{
  SCOTCH_Mesh m; SCOTCH_Geom g; int fd0, fd1, ierr = -1;
  SCOTCH_meshInit (&m); SCOTCH_geomInit (&g);
  fd0 = open (argv[1], O_RDONLY); fd1 = open ("/dev/null", O_RDONLY);
  scotchfmeshgeomloadhabo_ (&m, &g, &fd0, &fd1, "0", &ierr, 1);
  printf ("ierr=%d check=%d\n", ierr, (ierr == 0) ? SCOTCH_meshCheck (&m) : -1);
  if (ierr == 0) SCOTCH_meshExit (&m);
  SCOTCH_geomExit (&g);
  return (0);
}
