/* LD_PRELOAD malloc fault injector: the FAIL_NTH-th call to malloc (1-based,
** counted from program start) returns NULL; FAIL_NTH=0 disables injection.
** At exit, prints the number of malloc calls seen and the number of blocks
** still outstanding (allocated after the FAIL_SKIP-th call and never freed),
** a crude leak detector for non-sanitized builds.
** Build: gcc -O0 -shared -fPIC -o failmalloc.so failmalloc.c -ldl  */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void * (* real_malloc)  (size_t) = NULL;
static void   (* real_free)    (void *) = NULL;
static void * (* real_realloc) (void *, size_t) = NULL;
static long           callnbr = 0;
static long           failnth = -1;
static long           livenbr = 0;
static int            initflag = 0;
static char           bootbuf[65536];
static size_t         bootidx = 0;

static void
fm_init (void)
{
  const char *        s;

  if (initflag != 0)
    return;
  initflag = 1;
  real_malloc  = dlsym (RTLD_NEXT, "malloc");
  real_free    = dlsym (RTLD_NEXT, "free");
  real_realloc = dlsym (RTLD_NEXT, "realloc");
  s = getenv ("FAIL_NTH");
  failnth = (s != NULL) ? atol (s) : 0;
}

static void
fm_report (void)
{
  fprintf (stderr, "failmalloc: %ld malloc calls, %ld blocks never freed\n", callnbr, livenbr);
}

void *
malloc (size_t size)
{
  void *              p;

  if (real_malloc == NULL) {                      /* dlsym itself may call malloc */
    if (initflag != 0) {                          /* Bootstrap allocation         */
      p = bootbuf + bootidx;
      bootidx += (size + 15) & ~(size_t) 15;
      return (p);
    }
    fm_init ();
    atexit (fm_report);
  }
  callnbr ++;
  if (callnbr == failnth) {
    fprintf (stderr, "failmalloc: failing malloc call #%ld (size %zu)\n", callnbr, size);
    return (NULL);
  }
  p = real_malloc (size);
  if (p != NULL)
    livenbr ++;
  return (p);
}

void
free (void * p)
{
  if (p == NULL)
    return;
  if (((char *) p >= bootbuf) && ((char *) p < bootbuf + sizeof (bootbuf)))
    return;
  if (real_free == NULL)
    fm_init ();
  livenbr --;
  real_free (p);
}

void *
realloc (void * p, size_t size)
{
  void *              q;

  if (real_realloc == NULL)
    fm_init ();
  callnbr ++;
  if (callnbr == failnth) {
    fprintf (stderr, "failmalloc: failing realloc call #%ld (size %zu)\n", callnbr, size);
    return (NULL);
  }
  q = real_realloc (p, size);
  if ((p == NULL) && (q != NULL))
    livenbr ++;
  return (q);
}
