/* LD_PRELOAD malloc fault injector. Env: FAIL_NTH=k fails the k-th malloc/realloc/calloc call (1-based);
** FAIL_ALL=1 makes every call after the k-th fail too. Prints the final call count on exit when FAIL_COUNT=1.
** Use with ASan: LD_PRELOAD=./failmalloc.so ASAN_OPTIONS=verify_asan_link_order=0 ... (ASan's allocator is next in chain). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <execinfo.h>

static void * (* real_malloc)  (size_t) = NULL;
static void * (* real_realloc) (void *, size_t) = NULL;
static void * (* real_calloc)  (size_t, size_t) = NULL;
static long   callnbr = 0;
static long   failnth = -1;
static int    failall = 0;
static int    initflag = 0;
static int    envflag  = 0;                       /* Set once the environment has been read */
extern char ** environ;
static char   bootbuf[65536];
static size_t bootpos = 0;

static void
fm_init (void)
{
  const char * s;
  if (initflag != 0) return;
  initflag = 1;
  real_malloc  = dlsym (RTLD_NEXT, "malloc");
  real_realloc = dlsym (RTLD_NEXT, "realloc");
  real_calloc  = dlsym (RTLD_NEXT, "calloc");
}

static void
fm_env (void)                                      /* Environment is not available in the earliest calls, so read it lazily */
{
  const char * s;
  if (environ == NULL) return;
  envflag = 1;
  s = getenv ("FAIL_NTH"); failnth = (s != NULL) ? atol (s) : -1;
  s = getenv ("FAIL_ALL"); failall = (s != NULL) ? atoi (s) : 0;
}

static int
fm_fail (void)
{
  callnbr ++;
  if (envflag == 0) fm_env ();
  if (failnth < 0) return (0);
  if (callnbr == failnth) return (1);
  if (failall && callnbr > failnth) return (1);
  return (0);
}

static void __attribute__ ((destructor))
fm_exit (void)
{
  if (getenv ("FAIL_COUNT") != NULL) {
    char buf[64]; int l = snprintf (buf, sizeof (buf), "FAILMALLOC calls=%ld\n", callnbr);
    write (2, buf, l);
  }
}

void *
malloc (size_t sz)
{
  if (initflag == 0) {                            /* dlsym may call malloc/calloc: serve from a static buffer */
    if (real_malloc == NULL && initflag == 0) {
      static int inboot = 0;
      if (inboot) { void * p = bootbuf + bootpos; bootpos += (sz + 15) & ~15; return (p); }
      inboot = 1; fm_init (); inboot = 0;
    }
  }
  if (fm_fail ()) return (NULL);
  return (real_malloc (sz));
}

void *
calloc (size_t n, size_t sz)
{
  if (initflag == 0) {
    static int inboot = 0;
    if (inboot) { void * p = bootbuf + bootpos; bootpos += (n * sz + 15) & ~15; memset (p, 0, n * sz); return (p); }
    inboot = 1; fm_init (); inboot = 0;
  }
  if (fm_fail ()) return (NULL);
  return (real_calloc (n, sz));
}

void *
realloc (void * p, size_t sz)
{
  if (initflag == 0) fm_init ();
  if (envflag == 0) fm_env ();
  if (environ != NULL && getenv ("FAIL_TRACE") != NULL) { void * bt[6]; int n = backtrace (bt, 6); { char b[48]; int l = snprintf (b, sizeof (b), "REALLOC-TRACE n=%ld\n", callnbr + 1); write (2, b, l); } backtrace_symbols_fd (bt, n, 2); }
  if (fm_fail ()) return (NULL);
  return (real_realloc (p, sz));
}
