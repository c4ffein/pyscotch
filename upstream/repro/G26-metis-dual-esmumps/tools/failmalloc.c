/* LD_PRELOAD malloc fault injector.
** FAILMALLOC_AT=N     : the N-th allocation call (malloc/calloc/realloc, counted from program
**                       start) returns NULL.
** FAILMALLOC_FUNC=sym : only allocations whose immediate caller is the function "sym" (dladdr
**                       on the return address; needs exported symbols) are counted, and the
**                       FAILMALLOC_NTH-th of them (default 1) returns NULL.
** FAILMALLOC_TRACE=1  : print what is failed and the counts at exit.
** Not thread-safe (fine for the sequential and small MPI tests). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static long                 failat = -1;
static long                 count  = 0;
static const char *         failfunc = NULL;
static long                 failnth  = 1;
static long                 funccount = 0;
static int                  inited = 0;
static void *            (* real_malloc)  (size_t);
static void *            (* real_calloc)  (size_t, size_t);
static void *            (* real_realloc) (void *, size_t);
static char                 bootbuf[65536];        /* For dlsym's own calloc during init */
static size_t               bootpos = 0;

static void
init (void)
{
  const char *        s;

  if (inited)
    return;
  inited = 1;
  real_malloc  = dlsym (RTLD_NEXT, "malloc");
  real_calloc  = dlsym (RTLD_NEXT, "calloc");
  real_realloc = dlsym (RTLD_NEXT, "realloc");
  s = getenv ("FAILMALLOC_AT");
  failat = (s != NULL) ? atol (s) : -1;
  failfunc = getenv ("FAILMALLOC_FUNC");
  s = getenv ("FAILMALLOC_NTH");
  failnth = (s != NULL) ? atol (s) : 1;
}

static int
hit2 (void * retaddr)
{
  Dl_info             info;

  count ++;
  if (count == failat) {
    if (getenv ("FAILMALLOC_TRACE") != NULL)
      fprintf (stderr, "failmalloc: failing allocation #%ld\n", count);
    return (1);
  }
  if (failfunc != NULL) {
    if ((dladdr (retaddr, &info) != 0) && (info.dli_sname != NULL) && (strcmp (info.dli_sname, failfunc) == 0)) {
      funccount ++;
      if (funccount == failnth) {
        if (getenv ("FAILMALLOC_TRACE") != NULL)
          fprintf (stderr, "failmalloc: failing allocation #%ld in %s (#%ld overall)\n", funccount, failfunc, count);
        return (1);
      }
    }
  }
  return (0);
}

#define hit() hit2 (__builtin_return_address (0))

static void __attribute__ ((destructor))
fini (void)
{
  if (getenv ("FAILMALLOC_TRACE") != NULL)
    fprintf (stderr, "failmalloc: %ld allocations seen, %ld in %s\n", count, funccount, (failfunc != NULL) ? failfunc : "(no function)");
}

void *
malloc (size_t n)
{
  if (! inited) {
    init ();
  }
  if (real_malloc == NULL) {                      /* During dlsym bootstrap */
    void * p = bootbuf + bootpos;
    bootpos += (n + 15) & ~15;
    return (p);
  }
  if (hit ())
    return (NULL);
  return (real_malloc (n));
}

void *
calloc (size_t a, size_t b)
{
  if (! inited)
    init ();
  if (real_calloc == NULL) {
    void * p = bootbuf + bootpos;
    bootpos += (a * b + 15) & ~15;
    memset (p, 0, a * b);
    return (p);
  }
  if (hit ())
    return (NULL);
  return (real_calloc (a, b));
}

void *
realloc (void * p, size_t n)
{
  if (! inited)
    init ();
  if (hit ())
    return (NULL);
  return (real_realloc (p, n));
}
