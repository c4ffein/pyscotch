/* API-23: SCOTCH_graphMap with parttab==NULL; graphMapInit allocates parttab.
** If that allocation fails, pristine ignores the error and crashes in graphMapCompute. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char ** argv) {
  int w = 8; SCOTCH_Num n = w*w, e = 0, i;
  SCOTCH_Num * vt = malloc ((n+1)*sizeof (SCOTCH_Num));
  SCOTCH_Num * et = malloc (4*n*sizeof (SCOTCH_Num));
  SCOTCH_Graph g; SCOTCH_Arch a; SCOTCH_Strat s; int r;
  for (i = 0; i < n; i ++) { int x=i%w,y=i/w; vt[i]=e;
    if(x>0)et[e++]=i-1; if(x<w-1)et[e++]=i+1; if(y>0)et[e++]=i-w; if(y<w-1)et[e++]=i+w; }
  vt[n]=e;
  SCOTCH_graphInit (&g); SCOTCH_graphBuild (&g,0,n,vt,NULL,NULL,NULL,e,et,NULL);
  SCOTCH_archInit (&a); SCOTCH_archCmplt (&a,4); SCOTCH_stratInit (&s);
  r = SCOTCH_graphMap (&g, &a, &s, NULL);          /* parttab NULL -> Init allocates it */
  printf ("SCOTCH_graphMap ret=%d\n", r);
  return (r != 0);
}
