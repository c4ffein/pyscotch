/* LD_PRELOAD shim: make the FAIL_AT-th call to malloc() return NULL.
** Forwards to the next malloc in the search order (ASan's when the
** program is sanitized), so that ASan keeps tracking allocations. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void * (* realmalloc) (size_t) = NULL;
static char         bootbuf[65536];
static size_t       bootpos = 0;
static int          mallocnbr = 0;
static int          failnum = -1;
static int          initing = 0;

void *
malloc (
size_t              n)
{
  if (realmalloc == NULL) {
    if (initing) {                                /* dlsym() needs memory: serve it from a static arena */
      void *      p = bootbuf + bootpos;
      bootpos += (n + 15) & ~(size_t) 15;
      return (p);
    }
    initing = 1;
    realmalloc = (void * (*) (size_t)) dlsym (RTLD_NEXT, "malloc");
    failnum = getenv ("FAIL_AT") ? atoi (getenv ("FAIL_AT")) : -1;
    initing = 0;
  }
  if (++ mallocnbr == failnum) {
    fprintf (stderr, "failmalloc: failing malloc call #%d (%zu bytes)\n", mallocnbr, n);
    return (NULL);
  }
  return (realmalloc (n));
}
