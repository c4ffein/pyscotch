#include <stdint.h>
#include <stdio.h>
#include "scotch.h"
extern void scotchfgraphinducelist_(SCOTCH_Graph*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Graph*,int*);
extern void scotchfgraphinducepart_(SCOTCH_Graph*,SCOTCH_Num*,SCOTCH_GraphPart2*,SCOTCH_GraphPart2*,SCOTCH_Graph*,int*);
int main(){
  SCOTCH_Num vt[5]={0,1,3,5,6}, et[6]={1,0,2,1,3,2};
  SCOTCH_Graph g,ig; SCOTCH_graphInit(&g); SCOTCH_graphBuild(&g,0,4,vt,NULL,NULL,NULL,6,et,NULL);
  SCOTCH_Num lst[2]={1,2}, n=2; SCOTCH_GraphPart2 pt[4]={0,1,1,0}, pv=1; int ierr=-1;
  SCOTCH_graphInit(&ig); scotchfgraphinducelist_(&g,&n,lst,&ig,&ierr);
  SCOTCH_Num vn,en; SCOTCH_graphSize(&ig,&vn,&en); printf("induceList ierr=%d vertnbr=%ld edgenbr=%ld (expect 2,2)\n",ierr,(long)vn,(long)en);
  SCOTCH_Graph ig2; SCOTCH_graphInit(&ig2); scotchfgraphinducepart_(&g,&n,pt,&pv,&ig2,&ierr);
  SCOTCH_Num ptt[4]; (void)ptt;
  SCOTCH_graphSize(&ig2,&vn,&en); printf("inducePart ierr=%d vertnbr=%ld edgenbr=%ld\n",ierr,(long)vn,(long)en);
  return 0;}
