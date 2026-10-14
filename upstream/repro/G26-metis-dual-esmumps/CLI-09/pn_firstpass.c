#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
typedef int idx_t;
int ParMETIS_V3_NodeND(idx_t*,idx_t*,idx_t*,idx_t*,idx_t*,idx_t*,idx_t*,MPI_Comm*);
int main(int c,char**v){ MPI_Init(&c,&v); int np,me; MPI_Comm_size(MPI_COMM_WORLD,&np); MPI_Comm_rank(MPI_COMM_WORLD,&me);
 int g=16, n=g*g; idx_t*vd=malloc((np+1)*sizeof(idx_t)); for(int p=0;p<=np;p++)vd[p]=(long)n*p/np;
 int lo=vd[me],hi=vd[me+1],ln=hi-lo; idx_t*x=malloc((ln+1)*sizeof(idx_t)),*a=malloc(4*ln*sizeof(idx_t)),*ord=malloc(ln*sizeof(idx_t)),*sz=malloc((2*np)*sizeof(idx_t)); int e=0;
 for(int u=lo;u<hi;u++){int i=u%g,j=u/g; x[u-lo]=e; if(i>0)a[e++]=u-1; if(i<g-1)a[e++]=u+1; if(j>0)a[e++]=u-g; if(j<g-1)a[e++]=u+g;} x[ln]=e;
 idx_t nf=0,opt[3]={0,0,0}; MPI_Comm cm=MPI_COMM_WORLD;
 int useNull = c>1; /* argv[1] => sizes=NULL */
 int r=ParMETIS_V3_NodeND(vd,x,a,&nf,opt,ord,useNull?NULL:sz,&cm);
 int mn=1<<30,mx=-1; for(int i=0;i<ln;i++){if(ord[i]<mn)mn=ord[i]; if(ord[i]>mx)mx=ord[i];}
 printf("rank %d/%d sizes=%s: ret=%d (METIS_OK=1) order range [%d,%d]\n",me,np,useNull?"NULL":"buf",r,mn,mx);
 MPI_Finalize(); return 0;}
