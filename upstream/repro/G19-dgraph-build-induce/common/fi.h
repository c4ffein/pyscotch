/* Arm the LD_PRELOAD fault injector (fishim.so), if present. */
#define _GNU_SOURCE
#include <dlfcn.h>
static void fi_arm (int v) { volatile long * p = (volatile long *) dlsym (RTLD_DEFAULT, "fi_armed"); if (p != NULL) *p = v; }
