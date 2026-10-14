#include <stdio.h>
#include <stdint.h>
#include "scotch.h"
/* With SCOTCH_NAME_SUFFIX builds, scotch.h declares suffixed names: compile with -DSUFFIX=_xxx */
#ifndef SUFFIX
#define SUFFIX
#endif
#define CAT(a, b) a##b
#define NAME2(a, b) CAT(a, b)
#define NAME(x) NAME2(x, SUFFIX)
int main (void) {
  NAME(SCOTCH_Graph) g;
  NAME(SCOTCH_graphInit) (&g);
  NAME(SCOTCH_graphExit) (&g);
#ifdef COMMON_RANDOM_FIXED_SEED
  printf ("COMMON_RANDOM_FIXED_SEED leaked into consumer\n");
#else
  printf ("no scotch-internal macros in consumer\n");
#endif
  return (0);
}
