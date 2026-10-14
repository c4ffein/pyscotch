/* LD_PRELOAD: fail the N-th realloc call (N from env GRA17_FAIL), to inject a resize failure. */
#define _GNU_SOURCE
#include <stdlib.h>
#include <dlfcn.h>
#include <stdio.h>
static void * (*real_realloc) (void *, size_t) = NULL;
static long   countdown = -1;
void * realloc (void * ptr, size_t size) {
  if (real_realloc == NULL) {
    real_realloc = dlsym (RTLD_NEXT, "realloc");
    const char * e = getenv ("GRA17_FAIL");
    countdown = (e != NULL) ? atol (e) : -1;
  }
  if (countdown > 0) {
    countdown --;
    if (countdown == 0) { fprintf (stderr, "[failrealloc] failing realloc(size=%zu)\n", size); return NULL; }
  }
  return real_realloc (ptr, size);
}
