/* COR-15: digit-string fuzz of intLoad() against strtoll().
** For each random string: intLoad must return 1 and the exact value when the
** value lies in [-INTVALMAX, INTVALMAX], and 0 when it does not (the single
** value -INTVALMAX-1 is rejected by design: digits are accumulated positively). Prints the first mismatches.
** Build with the Scotch internal headers (module.h / common.h) so that the
** SCOTCH_RENAME'd symbol is resolved. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include "module.h"
#include "common.h"

int
main (int argc, char * argv[])
{
  long                seedval = (argc > 1) ? atol (argv[1]) : 1;
  long                iternbr = (argc > 2) ? atol (argv[2]) : 200000;
  long                iternum;
  long                badnbr  = 0;
  char                strtab[64];
  const long long     intmax  = (long long) INTVALMAX;

  srand48 (seedval);
  printf ("sizeof (INT) = %d, INTVALMAX = %lld\n", (int) sizeof (INT), intmax);
  for (iternum = 0; iternum < iternbr; iternum ++) {
    int                 lennbr = 1 + (int) (lrand48 () % 22); /* 1..22 digits */
    int                 i, o;
    int                 sign   = (int) (lrand48 () % 3);      /* 0: none, 1: '-', 2: '+' */
    char *              ptr    = strtab;
    long long           refval;
    INT                 valval = (INT) 0x5a5a5a5a;
    FILE *              stream;

    if (lrand48 () % 4 == 0)                      /* Sometimes a string near the limit (unsigned arithmetic: no overflow) */
      sprintf (strtab, "%s%llu", ((lrand48 () % 2) != 0) ? "-" : "", (unsigned long long) intmax + (unsigned long long) (lrand48 () % 20) - 10ULL);
    else {
      if (sign == 1) *ptr ++ = '-';
      if (sign == 2) *ptr ++ = '+';
      for (i = 0; i < lennbr; i ++)
        *ptr ++ = '0' + (char) (lrand48 () % 10);
      *ptr = '\0';
    }
    errno  = 0;
    refval = strtoll (strtab, NULL, 10);
    stream = fmemopen (strtab, strlen (strtab), "r");
    o = intLoad (stream, &valval);
    fclose (stream);
    if ((errno == ERANGE) || (refval > intmax) || (refval < - intmax)) { /* Outside [-INTVALMAX, INTVALMAX]: must be rejected */
      if (o != 0) {
        if (badnbr ++ < 10)
          printf ("MISMATCH: \"%s\" out of range but intLoad returned %d with value %lld\n", strtab, o, (long long) valval);
      }
    }
    else {
      if ((o != 1) || ((long long) valval != refval)) {
        if (badnbr ++ < 10)
          printf ("MISMATCH: \"%s\" expected %lld, intLoad returned %d with value %lld\n", strtab, refval, o, (long long) valval);
      }
    }
  }
  printf ("%ld strings, %ld mismatches\n", iternbr, badnbr);
  return ((badnbr != 0) ? 1 : 0);
}
