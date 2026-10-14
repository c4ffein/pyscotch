/* LD_PRELOAD malloc: returns NULL on the N-th call (SCOTCH_FAIL_AT), and at exit
** prints how many malloc calls happened AFTER that failure (post-failure activity). */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
static long count = 0, failat = -1, postcnt = 0, failed = 0;
static void report (void) { fprintf (stderr, "[failmalloc] total=%ld postfail=%ld\n", count, postcnt); }
void * malloc (size_t size) {
  static void * (*real) (size_t) = NULL;
  if (real == NULL) { real = dlsym (RTLD_NEXT, "malloc");
    { const char * e = getenv ("SCOTCH_FAIL_AT"); failat = (e != NULL) ? atol (e) : -1; } atexit (report); }
  count ++;
  if (failed) postcnt ++;
  if ((failat > 0) && (count == failat)) { failed = 1; fprintf (stderr, "[failmalloc] NULL at call %ld size=%zu\n", count, size); return NULL; }
  return real (size);
}
