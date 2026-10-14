#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main(int argc,char**argv){
  int dup=atoi(argv[1]);
  SCOTCH_Num vt[5]={0,1,3,5,6}, et[6]={1,0,2,1,3,2}; SCOTCH_Num lb1[4]={0,1,2,3}, lb2[4]={0,0,1,2};
  SCOTCH_Graph g; SCOTCH_graphInit(&g); SCOTCH_graphBuild(&g,0,4,vt,NULL,NULL,NULL,6,et,NULL);
  /* labelled graph needs vlbltab */
  SCOTCH_graphInit(&g); SCOTCH_graphBuild(&g,0,4,vt,NULL,NULL,dup?lb2:lb1,6,et,NULL);
  printf("graphCheck=%d\n",SCOTCH_graphCheck(&g));
  FILE*f=fopen("map1.txt","w"); fprintf(f,"1\n0 5\n"); fclose(f);
  SCOTCH_Num pt[4]; f=fopen("map1.txt","r"); int r=SCOTCH_graphTabLoad(&g,pt,f); fclose(f);
  printf("r=%d parttab=%ld %ld %ld %ld\n",r,(long)pt[0],(long)pt[1],(long)pt[2],(long)pt[3]);
  return 0;}
