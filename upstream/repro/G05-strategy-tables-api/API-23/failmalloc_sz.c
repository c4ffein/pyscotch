#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
static long count=0; 
void * malloc (size_t size){ static void*(*r)(size_t)=NULL; if(!r)r=dlsym(RTLD_NEXT,"malloc"); count++; if(getenv("SZTRACE")) fprintf(stderr,"m %ld %zu\n",count,size); return r(size);} 
