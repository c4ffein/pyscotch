/* LD_PRELOAD malloc/realloc fault injector.
** Env: FI_RANK (MPI rank to fail, from OMPI_COMM_WORLD_RANK; -1 = all ranks),
**      FI_NTH  (0-based index of the counted allocation that fails, after arming).
** The program arms the shim by setting the exported variable fi_armed to 1
** (resolve it with dlsym (RTLD_DEFAULT, "fi_armed") so that it links without the shim).
** Only allocations whose caller lies in a library whose path contains "scotch" are counted.
** fi_seen counts allocations seen while armed. Use ASAN_OPTIONS=verify_asan_link_order=0.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <execinfo.h>

volatile long fi_armed = 0;
volatile long fi_seen  = 0;
static long   fi_rank  = -2;
static long   fi_nth   = -1;
static long   fi_log   = 0;
static const char * fi_func = NULL;
static int    fi_init  = 0;
static int    fi_inbt  = 0;                      /* Set while backtrace() runs, so that its own allocations are not counted */
static void * (*real_malloc)  (size_t) = NULL;
static void * (*real_realloc) (void *, size_t) = NULL;
static void * (*real_calloc)  (size_t, size_t) = NULL;
static void   (*real_free)    (void *) = NULL;
static char   bootbuf[65536];
static size_t bootoff = 0;

static int
fi_myrank (void)
{
  const char * s = getenv ("OMPI_COMM_WORLD_RANK");
  if (s == NULL) s = getenv ("PMI_RANK");
  return (s != NULL) ? atoi (s) : 0;
}

static void
fi_segv (int sig)
{
  void *              tab[64];
  int                 n = backtrace (tab, 64);
  fprintf (stderr, "fishim: rank %d: signal %d, backtrace:\n", fi_myrank (), sig);
  backtrace_symbols_fd (tab, n, 2);
  signal (sig, SIG_DFL);
  raise (sig);
}

__attribute__ ((constructor)) static void
fi_ctor (void)
{
  signal (SIGSEGV, fi_segv);
  signal (SIGBUS,  fi_segv);
  signal (SIGABRT, fi_segv);
  signal (SIGUSR1, fi_segv);                      /* Print a backtrace on demand (hang diagnosis) */
}

static void
fi_setup (void)
{
  const char * s;
  real_malloc  = (void * (*) (size_t)) dlsym (RTLD_NEXT, "malloc");
  real_realloc = (void * (*) (void *, size_t)) dlsym (RTLD_NEXT, "realloc");
  real_calloc  = (void * (*) (size_t, size_t)) dlsym (RTLD_NEXT, "calloc");
  real_free    = (void (*) (void *)) dlsym (RTLD_NEXT, "free");
  fi_rank = ((s = getenv ("FI_RANK")) != NULL) ? atol (s) : -1;
  fi_nth  = ((s = getenv ("FI_NTH"))  != NULL) ? atol (s) : -1;
  fi_log  = ((s = getenv ("FI_LOG"))  != NULL) ? atol (s) : 0;
  fi_func = getenv ("FI_FUNC");
  fi_init = 1;
  {                                               /* Warm up backtrace() so that it does not allocate later */
    void * tab[4];
    fi_inbt = 1;
    backtrace (tab, 4);
    fi_inbt = 0;
  }
}


static int
fi_match (void)                                   /* Does some frame above malloc belong to routine FI_FUNC? */
{
  void *              tab[8];
  int                 n;
  int                 i;

  if (fi_func == NULL)
    return (1);
  fi_inbt = 1;
  n = backtrace (tab, 8);
  fi_inbt = 0;
  for (i = 1; i < n; i ++) {
    Dl_info             info;

    if (dladdr (tab[i], &info) != 0 && info.dli_sname != NULL && strstr (info.dli_sname, fi_func) != NULL)
      return (1);
  }
  return (0);
}

static int
fi_fail (void * retadr)
{
  Dl_info             info;

  if (fi_armed == 0 || (fi_nth < 0 && fi_log == 0))
    return (0);
  if ((fi_rank != -1) && (fi_rank != fi_myrank ()))
    return (0);
  if (dladdr (retadr, &info) == 0 || info.dli_fname == NULL || strstr (info.dli_fname, "scotch") == NULL)
    return (0);                                   /* Only count allocations made by the Scotch libraries (not MPI) */
  if (fi_match () == 0)
    return (0);                                   /* Only count allocations requested under the given (exported) routine */
  if (fi_log != 0)
    fprintf (stderr, "fishim: rank %d: alloc #%ld from %s\n", fi_myrank (), fi_seen, (info.dli_sname != NULL) ? info.dli_sname : "?");
  if (fi_seen ++ == fi_nth) {
    fprintf (stderr, "fishim: rank %d: failing allocation #%ld\n", fi_myrank (), fi_nth);
    return (1);
  }
  return (0);
}

void *
malloc (size_t n)
{
  if (fi_init == 0) {
    if (real_malloc == NULL && bootoff + n + 16 < sizeof (bootbuf)) { /* Bootstrap allocations while dlsym runs */
      void * p = bootbuf + bootoff;
      bootoff += (n + 15) & ~(size_t) 15;
      return (p);
    }
    fi_setup ();
  }
  if (fi_inbt != 0)
    return (real_malloc (n));
  if (fi_fail (__builtin_return_address (0)))
    return (NULL);
  return (real_malloc (n));
}

static int
fi_isboot (const void * p)
{
  return ((const char *) p >= bootbuf && (const char *) p < bootbuf + sizeof (bootbuf));
}

void *
calloc (size_t m, size_t n)
{
  if (fi_init == 0) {
    void * p = malloc (m * n);                    /* Bootstrap buffer is zeroed */
    if (p != NULL && ! fi_isboot (p)) memset (p, 0, m * n);
    return (p);
  }
  return (real_calloc (m, n));
}

void
free (void * p)
{
  if (p == NULL || fi_isboot (p))
    return;
  if (fi_init == 0)
    fi_setup ();
  real_free (p);
}

void *
realloc (void * p, size_t n)
{
  if (fi_init == 0)
    fi_setup ();
  if (fi_inbt != 0)
    return (real_realloc (p, n));
  if (fi_fail (__builtin_return_address (0)))
    return (NULL);
  if (fi_isboot (p)) {                            /* Bootstrap block */
    void * q = real_malloc (n);
    if (q != NULL) memcpy (q, p, n);
    return (q);
  }
  return (real_realloc (p, n));
}
