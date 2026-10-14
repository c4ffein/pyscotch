/* PS-SEP-6: intRandVal2() is declared UINT64 but returns (UINT) intRandVal3().
** Print the first values and the OR of the high 32 bits over many draws. */
#include <stdio.h>
#include <stdlib.h>
#include "module.h"
#include "common.h"

int
main (void)
{
  IntRandContext      randdat;
  uint64_t            highval = 0;
  int                 i;

  randdat.flagval = 0;
  intRandProc (&randdat, 0);
  intRandInit (&randdat);
  printf ("sizeof (UINT) = %d\n", (int) sizeof (UINT));
  for (i = 0; i < 4; i ++)
    printf ("intRandVal2 = 0x%016llx\n", (unsigned long long) intRandVal2 (&randdat));
  for (i = 0; i < 100000; i ++)
    highval |= (intRandVal2 (&randdat) >> 32);
  printf ("OR of high 32 bits over 100000 draws = 0x%08llx\n", (unsigned long long) highval);
  return (0);
}
