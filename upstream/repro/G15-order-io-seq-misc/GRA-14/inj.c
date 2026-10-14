/* LD_PRELOAD allocation-failure injector (works under ASan with
** ASAN_OPTIONS=verify_asan_link_order=0).
** The harness sets inj_countdown = N (> 0) to make the N-th subsequent
** malloc/realloc return NULL (once); inj_fired tells whether it did.
*/
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>

volatile long       inj_countdown = 0;            /* 0: disabled; N: fail N-th call */
volatile long       inj_fired     = 0;
volatile long       inj_calls     = 0;            /* Calls seen while enabled */

static void * (* real_malloc)  (size_t)         = NULL;
static void * (* real_realloc) (void *, size_t) = NULL;

static int
inj_hit (void)
{
  if (inj_countdown <= 0)
    return (0);
  inj_calls ++;
  if (-- inj_countdown == 0) {
    inj_fired ++;
    return (1);
  }
  return (0);
}

void *
malloc (size_t size)
{
  if (real_malloc == NULL)
    real_malloc = dlsym (RTLD_NEXT, "malloc");
  if (inj_hit ())
    return (NULL);
  return (real_malloc (size));
}

void *
realloc (void * ptr, size_t size)
{
  if (real_realloc == NULL)
    real_realloc = dlsym (RTLD_NEXT, "realloc");
  if (inj_hit ())
    return (NULL);
  return (real_realloc (ptr, size));
}
