/* LD_PRELOAD helper: fail the N-th malloc call (N = $FAILMALLOC), count calls in $FAILMALLOC_COUNT mode */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
static int failnum = -1, callnum = 0, init = 0;
static void * (*realmalloc) (size_t) = NULL;
void * malloc (size_t n) {
  if (! init) { init = 1; realmalloc = dlsym (RTLD_NEXT, "malloc"); const char * s = getenv ("FAILMALLOC"); failnum = (s != NULL) ? atoi (s) : -1; }
  callnum ++;
  if (callnum == failnum) return (NULL);
  return (realmalloc (n));
}
