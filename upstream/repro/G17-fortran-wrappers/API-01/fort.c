#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
extern void scotchfstratgraphorderbuild_(SCOTCH_Strat*,SCOTCH_Num*,SCOTCH_Num*,double*,int*);
extern void scotchfmeshgeomloadhabo_(SCOTCH_Mesh*,SCOTCH_Geom*,int*,int*,const char*,int*,int);
extern void scotchfarchsize_(SCOTCH_Arch*,SCOTCH_Num*);
int main(int argc,char**argv){
  setvbuf(stdout,NULL,_IONBF,0);
  int mode=atoi(argv[1]);
  if(mode==0){
    SCOTCH_Strat s1,s2; SCOTCH_stratInit(&s1);SCOTCH_stratInit(&s2);
    SCOTCH_Num flag=SCOTCH_STRATLEVELMAX, lev=7; double kb=0.1; int ierr=-1;
    SCOTCH_stratGraphOrderBuild(&s1,flag,lev,kb);
    scotchfstratgraphorderbuild_(&s2,&flag,&lev,&kb,&ierr);
    printf("C      : "); SCOTCH_stratSave(&s1,stdout); printf("\nFortran: ierr=%d ",ierr); SCOTCH_stratSave(&s2,stdout); printf("\n");
  }
  if(mode==1){
    SCOTCH_Mesh m; SCOTCH_meshInit(&m); SCOTCH_Geom g; SCOTCH_geomInit(&g);
    int f0=0,f1=0,ierr=-1;
    scotchfmeshgeomloadhabo_(&m,&g,&f0,&f1,"0",&ierr,1);
    printf("ierr=%d\n",ierr);
  }
  if(mode==2){
    SCOTCH_Arch a; SCOTCH_archInit(&a); SCOTCH_archCmplt(&a,70000);
    long long buf=0x5a5a5a5a5a5a5a5aLL; scotchfarchsize_(&a,(SCOTCH_Num*)&buf);
    printf("sizeof(SCOTCH_Num)=%zu, after ARCHSIZE buf=0x%llx (expect 0x11170 if Num is 64-bit)\n",sizeof(SCOTCH_Num),buf);
  }
  return 0;}
