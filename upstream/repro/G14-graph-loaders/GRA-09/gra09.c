#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
int main(void){
  SCOTCH_Graph g; SCOTCH_Geom ge; SCOTCH_Num dim; double *tab;
  FILE *fg=fopen("p4s.grf","r"),*fx=fopen("p4.xyz","r");
  SCOTCH_graphInit(&g); SCOTCH_geomInit(&ge);
  if(SCOTCH_graphGeomLoadScot(&g,&ge,fg,fx,NULL)) return 1;
  SCOTCH_geomData(&ge,&dim,&tab);
  printf("dim=%d tab=%p tab[2]=%f\n",(int)dim,(void*)tab,tab?tab[2]:-1.0);
  FILE *fo=fopen("/dev/stdout","w"); FILE *fo2=fopen("/dev/null","w");
  SCOTCH_graphGeomSaveScot(&g,&ge,fo2,fo,NULL); fclose(fo);
  return 0;}
