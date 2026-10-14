#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <stdint.h>
#include "ptscotch.h"
extern void scotchfdgraphmapstat_(SCOTCH_Dgraph*,SCOTCH_Dmapping*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,double*,double*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,SCOTCH_Num*,int*);
int main(int argc,char**argv){
  MPI_Init(&argc,&argv); int rk,np; MPI_Comm_rank(MPI_COMM_WORLD,&rk); MPI_Comm_size(MPI_COMM_WORLD,&np);
  setvbuf(stdout,NULL,_IONBF,0);
  /* 8x8 grid distributed by rows: 8/np rows per rank */
  int W=8,H=8,rows=H/np; SCOTCH_Num L=W*rows; SCOTCH_Num *vt=malloc((L+1)*sizeof*vt),*et=malloc(4*L*sizeof*et); int e=0;
  for(int r=0;r<rows;r++)for(int c=0;c<W;c++){int i=r*W+c, gr=rk*rows+r; vt[i]=e;
    if(gr>0)et[e++]=(gr-1)*W+c; if(gr<H-1)et[e++]=(gr+1)*W+c; if(c>0)et[e++]=gr*W+c-1; if(c<W-1)et[e++]=gr*W+c+1;} vt[L]=e;
  SCOTCH_Num *el=malloc(e*sizeof*el); for(int k=0;k<e;k++)el[k]=3; SCOTCH_Dgraph g; SCOTCH_dgraphInit(&g,MPI_COMM_WORLD);
  if(SCOTCH_dgraphBuild(&g,0,L,L,vt,NULL,NULL,NULL,e,e,et,NULL,el)) return 8;
  SCOTCH_Arch a; SCOTCH_archInit(&a); SCOTCH_archCmplt(&a,4);
  SCOTCH_Strat s; SCOTCH_stratInit(&s);
  SCOTCH_Dmapping m; SCOTCH_dgraphMapInit(&g,&m,&a,NULL);
  if(SCOTCH_dgraphMapCompute(&g,&m,&s)) return 7;
  SCOTCH_Num tg,mn,mi,ma,ns,ni,nx,cm,ct[256],lo,di,ex; double av,dl;
  SCOTCH_dgraphMapStat(&g,&m,&tg,&mn,&mi,&ma,&av,&dl,&ns,&ni,&nx,&cm,ct,&lo,&di,&ex);
  if(rk==0){ printf("cmlosum=%ld cmdisum=%ld cmexsum=%ld\n",(long)lo,(long)di,(long)ex);
    printf("edgeglbnbr=%ld\n",(long)(2*(2*W*H-W-H)));
    printf("sequential-formula CommDelta = (cmex*E)/(2*cmlo*cmdi) = %f\n", (double)ex*(2*(2*W*H-W-H))/(2.0*lo*di)); }
  { int ierr=-77; scotchfdgraphmapstat_(&g,&m,&tg,&mn,&mi,&ma,&av,&dl,&ns,&ni,&nx,&cm,ct,&lo,&di,&ex,&ierr); if(rk==0)printf("Fortran DGRAPHMAPSTAT ierr=%d (sentinel -77 = never written)\n",ierr);}
  SCOTCH_dgraphMapView(&g,&m,rk==0?stdout:NULL);
  MPI_Finalize(); return 0;}
