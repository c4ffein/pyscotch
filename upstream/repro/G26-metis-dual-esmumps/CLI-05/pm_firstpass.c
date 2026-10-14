#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int idx_t;
int METIS_PartMeshDual(const idx_t*ne,const idx_t*nn,const idx_t*eptr,const idx_t*eind,const idx_t*vwgt,const idx_t*vsize,const idx_t*ncommon,const idx_t*nparts,const double*tpwgts,const idx_t*options,idx_t*objval,idx_t*epart,idx_t*npart);
int METIS_SetDefaultOptions(idx_t*);
#define NUMBERING 17
#define OBJTYPE 1
int main(int argc,char**argv){
 int mode=atoi(argv[1]); int b=(mode==0||mode==2)?1:0;
 idx_t g=6; idx_t ne=g*g, nn=(g+1)*(g+1), nc=2, np=3, obj=0;
 idx_t*eptr=malloc((ne+1)*sizeof(idx_t)),*eind=malloc(4*ne*sizeof(idx_t)),*ep=malloc(ne*sizeof(idx_t)),*npart=malloc(nn*sizeof(idx_t));
 int k=0; for(int j=0;j<g;j++)for(int i=0;i<g;i++){eptr[j*g+i]=k+b; eind[k++]=j*(g+1)+i+b; eind[k++]=j*(g+1)+i+1+b; eind[k++]=(j+1)*(g+1)+i+1+b; eind[k++]=(j+1)*(g+1)+i+b;} eptr[ne]=k+b;
 idx_t opt[40]; METIS_SetDefaultOptions(opt); opt[NUMBERING]=b;
 if(mode==0||mode==1){ opt[OBJTYPE]=1; /* VOL, vsize NULL */
   int r=METIS_PartMeshDual(&ne,&nn,eptr,eind,NULL,NULL,&nc,&np,NULL,opt,&obj,ep,npart); printf("mode %d (OBJTYPE=VOL, vsize=NULL, base %d): ret=%d objval=%d\n",mode,b,r,obj);}
 else { /* Fortran 'null' vwgt == ne */
   int r=METIS_PartMeshDual(&ne,&nn,eptr,eind,&ne,NULL,&nc,&np,NULL,opt,&obj,ep,npart); printf("mode %d (vwgt==&ne, base %d): ret=%d objval=%d\n",mode,b,r,obj);}
 return 0;}
