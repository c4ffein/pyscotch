#include <stdio.h>
#include <stdlib.h>
int main(){ int i; for(i=1;i<=5;i++){ void*p=malloc(10); printf("%d %s\n",i,p?"ok":"NULL"); free(p);} return 0;}
