/* LD_PRELOAD malloc/realloc fault injector with live-block accounting (extends G18's fishim.c).
** Env: FI_FUNC (optional: only allocations whose calling routine name contains it are counted),
**      FI_RANK (MPI rank to fail, from OMPI_COMM_WORLD_RANK; -1 = all ranks),
**      FI_NTH  (0-based index of the counted allocation that fails, after arming; -1 = never),
**      FI_LOG  (1: print every counted allocation with its calling routine).
** The program arms the shim by setting the exported variable fi_armed to 1 (dlsym (RTLD_DEFAULT, "fi_armed")).
** Only allocations whose caller lies in a library whose path contains "scotch" are counted; the calling
** routine is the first frame outside the Scotch memory wrappers (memAllocGroup, memReallocGroup, ...).
** Every block allocated by a Scotch library (armed or not) is recorded; at process exit, the number of
** blocks still allocated is printed ("fishim: rank r: live scotch blocks N"): a leak detector that works
** with MPI (MPI blocks are not recorded) and does not need ASan.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <pthread.h>
#include <execinfo.h>

volatile long fi_armed = 0;
volatile long fi_seen  = 0;
static long   fi_rank  = -2;
static long   fi_nth   = -1;
static long   fi_log   = 0;
static const char * fi_func = NULL;              /* FI_FUNC: count only allocations whose calling routine contains this string */
static int    fi_init  = 0;
static void * (*real_malloc)  (size_t) = NULL;
static void * (*real_realloc) (void *, size_t) = NULL;
static void * (*real_calloc)  (size_t, size_t) = NULL;
static void   (*real_free)    (void *) = NULL;
static char   bootbuf[65536];
static size_t bootoff = 0;
static pthread_mutex_t fi_mutex = PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;
static __thread int fi_inside = 0;

#define LIVEMAX (1 << 20)
static void * livetab[LIVEMAX];                   /* Open addressing hash of live Scotch blocks */
static long   livenbr = 0;
static long   livemax = 0;

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

static void
fi_report (void)
{
  fprintf (stderr, "fishim: rank %d: live scotch blocks %ld (max %ld)\n", fi_myrank (), livenbr, livemax);
}

__attribute__ ((constructor)) static void
fi_ctor (void)
{
  signal (SIGSEGV, fi_segv);
  signal (SIGBUS,  fi_segv);
  signal (SIGABRT, fi_segv);
  atexit (fi_report);
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
}

static size_t
fi_hash (const void * p)
{
  return ((((size_t) p) >> 4) * 2654435761u) & (LIVEMAX - 1);
}

static void
fi_liveadd (void * p)
{
  size_t h;
  if (p == NULL) return;
  for (h = fi_hash (p); livetab[h] != NULL; h = (h + 1) & (LIVEMAX - 1)) ;
  livetab[h] = p;
  if (++ livenbr > livemax) livemax = livenbr;
}

static int
fi_livedel (void * p)                             /* Returns 1 if p was a recorded Scotch block */
{
  size_t h, i, j;
  if (p == NULL) return (0);
  for (h = fi_hash (p); livetab[h] != NULL; h = (h + 1) & (LIVEMAX - 1)) {
    if (livetab[h] == p) {
      livetab[h] = NULL; livenbr --;              /* Re-insert following cluster entries */
      for (i = (h + 1) & (LIVEMAX - 1); livetab[i] != NULL; i = (i + 1) & (LIVEMAX - 1)) {
        void * q = livetab[i]; livetab[i] = NULL;
        for (j = fi_hash (q); livetab[j] != NULL; j = (j + 1) & (LIVEMAX - 1)) ;
        livetab[j] = q;
      }
      return (1);
    }
  }
  return (0);
}

static int
fi_isscotch (void * retadr, const char ** symptr)
{
  Dl_info             info;
  if (dladdr (retadr, &info) == 0 || info.dli_fname == NULL || strstr (info.dli_fname, "scotch") == NULL)
    return (0);
  *symptr = (info.dli_sname != NULL) ? info.dli_sname : "?";
  return (1);
}

static const char *
fi_caller (void * retadr)                         /* Name of the first Scotch routine outside the memory wrappers */
{
  void *              tab[8];
  int                 n, i;
  const char *        sym = "?";

  if (! fi_isscotch (retadr, &sym))
    return (NULL);
  if (strstr (sym, "memAlloc") == NULL && strstr (sym, "memRealloc") == NULL)
    return (sym);
  n = backtrace (tab, 8);
  for (i = 2; i < n; i ++) {
    const char *        s = "?";
    if (! fi_isscotch (tab[i], &s))
      continue;
    if (strstr (s, "memAlloc") == NULL && strstr (s, "memRealloc") == NULL)
      return (s);
  }
  return (sym);
}

static int
fi_fail (void * retadr, int * scotchptr)          /* Decide whether this allocation fails; tell if Scotch block */
{
  const char *        sym;

  *scotchptr = 0;
  if (fi_inside)
    return (0);
  fi_inside = 1;
  sym = fi_caller (retadr);
  fi_inside = 0;
  if (sym == NULL)
    return (0);
  *scotchptr = 1;
  if (fi_armed == 0 || (fi_nth < 0 && fi_log == 0))
    return (0);
  if ((fi_rank != -1) && (fi_rank != fi_myrank ()))
    return (0);
  if ((fi_func != NULL) && (strstr (sym, fi_func) == NULL))
    return (0);
  if (fi_log != 0)
    fprintf (stderr, "fishim: rank %d: alloc #%ld from %s\n", fi_myrank (), fi_seen, sym);
  if (fi_seen ++ == fi_nth) {
    fprintf (stderr, "fishim: rank %d: failing allocation #%ld in %s\n", fi_myrank (), fi_nth, sym);
    return (1);
  }
  return (0);
}

void *
malloc (size_t n)
{
  int                 isscotch;
  void *              p;

  if (fi_init == 0) {
    if (real_malloc == NULL && bootoff + n + 16 < sizeof (bootbuf)) { /* Bootstrap allocations while dlsym runs */
      p = bootbuf + bootoff;
      bootoff += (n + 15) & ~(size_t) 15;
      return (p);
    }
    fi_setup ();
  }
  if (fi_inside)                                  /* Nested allocation from backtrace(): no accounting */
    return (real_malloc (n));
  pthread_mutex_lock (&fi_mutex);
  if (fi_fail (__builtin_return_address (0), &isscotch)) {
    pthread_mutex_unlock (&fi_mutex);
    return (NULL);
  }
  p = real_malloc (n);
  if (isscotch)
    fi_liveadd (p);
  pthread_mutex_unlock (&fi_mutex);
  return (p);
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
  if (fi_inside) {
    real_free (p);
    return;
  }
  pthread_mutex_lock (&fi_mutex);
  fi_livedel (p);
  real_free (p);
  pthread_mutex_unlock (&fi_mutex);
}

void *
realloc (void * p, size_t n)
{
  int                 isscotch;
  void *              q;

  if (fi_init == 0)
    fi_setup ();
  if (fi_isboot (p)) {                            /* Bootstrap block */
    q = real_malloc (n);
    if (q != NULL) memcpy (q, p, n);
    return (q);
  }
  pthread_mutex_lock (&fi_mutex);
  if (fi_fail (__builtin_return_address (0), &isscotch)) {
    pthread_mutex_unlock (&fi_mutex);
    return (NULL);
  }
  q = real_realloc (p, n);
  if (q != NULL) {                                /* Old block consumed (even when q == p, the record is refreshed) */
    if (fi_livedel (p) || isscotch)
      fi_liveadd (q);
  }
  pthread_mutex_unlock (&fi_mutex);
  return (q);
}
