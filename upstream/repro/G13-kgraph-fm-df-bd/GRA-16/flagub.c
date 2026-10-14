/* GRA-16: the common.h flag-set macros expand to (1 << bit); when bit==31 this shifts into the
** sign bit of int -> undefined behaviour. This isolates the exact expansion before/after the fix. */
#include <stdio.h>
#ifdef FIXED
#define flagSet(a,n)  (a)[(n) / (sizeof (unsigned int) << 3)] |= (1U << ((n) & ((sizeof (unsigned int) << 3) - 1)))
static unsigned int tab[2];
#else
#define flagSet(a,n)  (a)[(n) / (sizeof (int) << 3)] |= (1 << ((n) & ((sizeof (int) << 3) - 1)))
static int tab[2];
#endif
int main (void) { int n = 31; flagSet (tab, n); printf ("tab[0]=%u\n", (unsigned) tab[0]); return 0; }
