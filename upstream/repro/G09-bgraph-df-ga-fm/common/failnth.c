/* LD_PRELOAD fault injector: fails the N-th call of malloc and/or realloc.
** FAIL_MALLOC_NTH=n  : the n-th malloc call (1-based) returns NULL.
** FAIL_REALLOC_NTH=n : the n-th realloc call (1-based) returns NULL.
** FAIL_TRACE=1       : print the running call counts to stderr at exit. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <execinfo.h>

static void * (*real_malloc)  (size_t) = NULL;
static void * (*real_realloc) (void *, size_t) = NULL;
static long   mcnt = 0, rcnt = 0, mfail = -1, rfail = -1;
static int    inited = 0;
static int    envread = 0;
static char   bootbuf[65536];
static size_t bootoff = 0;

static void failnth_init (void)
{
  const char * s;
  inited = 1;
  real_malloc  = dlsym (RTLD_NEXT, "malloc");
  real_realloc = dlsym (RTLD_NEXT, "realloc");
}

static void failnth_env (void)                    /* Environment may not be usable at the very first call (ASan init) */
{
  const char * s;
  if (envread) return;
  s = getenv ("FAIL_MALLOC_NTH");  if (s != NULL) { mfail = atol (s); envread = 1; }
  s = getenv ("FAIL_REALLOC_NTH"); if (s != NULL) { rfail = atol (s); envread = 1; }
  if (getenv ("FAIL_TRACE") != NULL) envread = 1;
}

static void failnth_fini (void) __attribute__ ((destructor));
static void failnth_fini (void)
{
  if (getenv ("FAIL_TRACE") != NULL)
    fprintf (stderr, "failnth: malloc calls=%ld realloc calls=%ld\n", mcnt, rcnt);
}

void * malloc (size_t n)
{
  if (! inited) {                                 /* dlsym may itself malloc: serve it from a static arena */
    if (real_malloc == NULL && inited == 0) {
      static int bootstrapping = 0;
      if (bootstrapping) {
        void * p = bootbuf + bootoff;
        bootoff += (n + 15) & ~(size_t) 15;
        return p;
      }
      bootstrapping = 1;
      failnth_init ();
      bootstrapping = 0;
    }
  }
  failnth_env ();
  mcnt ++;
  if (mcnt == mfail) {
    fprintf (stderr, "failnth: failing malloc call #%ld (size %zu)\n", mcnt, n);
    return NULL;
  }
  return real_malloc (n);
}

void * realloc (void * p, size_t n)
{
  if (! inited)
    failnth_init ();
  failnth_env ();
  rcnt ++;
  if (rcnt == rfail) {
    fprintf (stderr, "failnth: failing realloc call #%ld (size %zu)\n", rcnt, n);
    if (getenv ("FAIL_BT") != NULL) { void * bt[16]; int k = backtrace (bt, 16); backtrace_symbols_fd (bt, k, 2); }
    return NULL;
  }
  return real_realloc (p, n);
}
