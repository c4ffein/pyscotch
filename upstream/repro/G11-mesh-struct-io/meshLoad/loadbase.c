/* Load a mesh file with a given base value and check it. usage: loadbase file base */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[])
{
  SCOTCH_Mesh m; FILE * f; int r, c;
  SCOTCH_meshInit (&m); f = fopen (argv[1], "r");
  r = SCOTCH_meshLoad (&m, f, atoi (argv[2])); fclose (f);
  c = (r == 0) ? SCOTCH_meshCheck (&m) : -1;
  printf ("load=%d check=%d\n", r, c);
  if (r == 0) { SCOTCH_meshSave (&m, stdout); SCOTCH_meshExit (&m); }
  return (0);
}
