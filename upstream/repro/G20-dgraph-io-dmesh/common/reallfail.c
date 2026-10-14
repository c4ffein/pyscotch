/* LD_PRELOAD: once armed (fi_armed=1), every realloc whose caller is in a
** "scotch" library returns NULL. Demonstrates an ignored-resize infinite loop.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
volatile long fi_armed = 0;
static void * (*real_realloc)(void *,size_t) = NULL;
static long n = 0;
void * realloc (void * p, size_t s) {
  Dl_info info;
  if (real_realloc == NULL) real_realloc = (void *(*)(void *,size_t)) dlsym (RTLD_NEXT, "realloc");
  if ((fi_armed != 0) && (dladdr (__builtin_return_address (0), &info) != 0) &&
      (info.dli_fname != NULL) && (strstr (info.dli_fname, "scotch") != NULL)) {
    if ((++ n % 1000000) == 0) fprintf (stderr, "[reallfail] realloc returning NULL (call #%ld)\n", n);
    return (NULL);
  }
  return (real_realloc (p, s));
}
