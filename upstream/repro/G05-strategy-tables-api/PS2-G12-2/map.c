/* PS2-G12-2: SCOTCH_graphMap with a refinement-only strategy (no initial-mapping method).
** The mapping part array is never allocated/initialised -> NULL deref in the method. */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main (int argc, char ** argv) {
  int w = 16; SCOTCH_Num n = w*w, e = 0, i;
  SCOTCH_Num * vt = malloc ((n+1)*sizeof (SCOTCH_Num));
  SCOTCH_Num * et = malloc (4*n*sizeof (SCOTCH_Num));
  SCOTCH_Num * pt = malloc (n*sizeof (SCOTCH_Num));
  SCOTCH_Graph g; SCOTCH_Arch a; SCOTCH_Strat s; int r;
  for (i=0;i<n;i++){int x=i%w,y=i/w;vt[i]=e; if(x>0)et[e++]=i-1; if(x<w-1)et[e++]=i+1; if(y>0)et[e++]=i-w; if(y<w-1)et[e++]=i+w;}
  vt[n]=e;
  SCOTCH_graphInit (&g); SCOTCH_graphBuild (&g,0,n,vt,NULL,NULL,NULL,e,et,NULL);
  SCOTCH_archInit (&a); SCOTCH_archCmplt (&a,4); SCOTCH_stratInit (&s);
  if (SCOTCH_stratGraphMap (&s, argv[1]) != 0) { puts ("strat err"); return 3; }
  r = SCOTCH_graphMap (&g, &a, &s, pt);
  SCOTCH_Num mx=-1; for(i=0;i<n;i++) if(pt[i]>mx)mx=pt[i];
  printf ("ret=%d maxpart=%ld\n", r, (long) mx);
  return 0;
}
