/* GRA-17: public API SCOTCH_graphMap with an explicit FM strategy on a grid; under SCOTCH_DEBUG_KGRAPH2
** the extended-edge array starts tiny so kgraphMapFmEdgeResize is exercised. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char * argv[]) {
  int w = atoi (argv[1]), k = atoi (argv[2]);
  SCOTCH_Num n = (SCOTCH_Num) w * w, e = 0, i;
  SCOTCH_Num * vt = malloc ((n+1)*sizeof(SCOTCH_Num)), * et = malloc (4*n*sizeof(SCOTCH_Num)), * pt = malloc (n*sizeof(SCOTCH_Num));
  SCOTCH_Graph g; SCOTCH_Arch a; SCOTCH_Strat s;
  for (i=0;i<n;i++){int x=i%w,y=i/w;vt[i]=e;if(x>0)et[e++]=i-1;if(x<w-1)et[e++]=i+1;if(y>0)et[e++]=i-w;if(y<w-1)et[e++]=i+w;} vt[n]=e;
  SCOTCH_graphInit(&g); if(SCOTCH_graphBuild(&g,0,n,vt,NULL,NULL,NULL,e,et,NULL))return 9;
  SCOTCH_archInit(&a); SCOTCH_archCmplt(&a,k); SCOTCH_stratInit(&s);
  if (argc>3 && SCOTCH_stratGraphMap(&s,argv[3])) return 3;
  int r = SCOTCH_graphMap(&g,&a,&s,pt); printf("ret=%d\n",r); return 0;
}
