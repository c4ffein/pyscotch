/* LD_PRELOAD shim: the FAIL_AT-th call to pthread_create() fails with EAGAIN */
#define _GNU_SOURCE
#include <pthread.h>
#include <dlfcn.h>
#include <stdlib.h>
#include <errno.h>

static int                  callnbr = 0;

int
pthread_create (
pthread_t *                 thidptr,
const pthread_attr_t *      attrptr,
void *                   (* funcptr) (void *),
void *                      argptr)
{
  static int             (* realptr) (pthread_t *, const pthread_attr_t *, void * (*) (void *), void *) = NULL;
  const char *              failstr;
  int                       failnum;

  if (realptr == NULL)
    realptr = dlsym (RTLD_NEXT, "pthread_create");
  failstr = getenv ("FAIL_AT");
  failnum = (failstr != NULL) ? atoi (failstr) : -1;
  if (++ callnbr == failnum)
    return (EAGAIN);

  return (realptr (thidptr, attrptr, funcptr, argptr));
}
