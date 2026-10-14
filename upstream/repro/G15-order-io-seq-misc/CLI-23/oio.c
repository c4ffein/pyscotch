/* CLI-23 harness for the esMUMPS ordering loader/saver (internal symbols
** _ESMUMPSorderLoad / _ESMUMPSorderSave of libesmumps.so).
** usage: oio <mode>
**   0 : load an ordering file whose permutation entry is out of range (7 for 3 vertices)
**   1 : load an ordering file with a negative column block count
**   2 : load an ordering file with a duplicate permutation value
**   3 : load an ordering file with an unsorted / out-of-range range array
**   4 : save an ordering with vertnbr == 0 (reads permtab[0] of an empty array)
**   5 : save a valid 3-vertex ordering, then reload it and check it (round trip)
**   6 : save on a stream that fails after the first write (transient error): status must be an error
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scotch.h"
#include "esmumps.h"

typedef SCOTCH_Num INT;                           /* esMUMPS integer type */

typedef struct Order_ {
  INT                       cblknbr;
  INT *                     rangtab;
  INT *                     permtab;
  INT *                     peritab;
} Order;

int                         _ESMUMPSorderInit  (Order * const);
void                        _ESMUMPSorderExit  (Order * const);
int                         _ESMUMPSorderLoad  (Order * const, FILE * const);
int                         _ESMUMPSorderSave  (const Order * const, FILE * const);
int                         _ESMUMPSorderCheck (const Order * const);

static int
loadstr (const char * const s, Order * const ordeptr)
{
  FILE * f = fmemopen ((void *) s, strlen (s), "r");
  int    r = _ESMUMPSorderLoad (ordeptr, f);
  fclose (f);
  return (r);
}

int
main (int argc, char * argv[])
{
  Order               ordedat;
  int                 mode = atoi (argv[1]);
  int                 r;

  _ESMUMPSorderInit (&ordedat);
  switch (mode) {
    case 0 : r = loadstr ("0\n1\t3\n0\t3\n0 7 1\n", &ordedat); printf ("load ret=%d\n", r); break;
    case 1 : r = loadstr ("0\n-1\t3\n0\t3\n0 2 1\n", &ordedat); printf ("load ret=%d\n", r); break;
    case 2 : r = loadstr ("0\n1\t3\n0\t3\n0 2 2\n", &ordedat); printf ("load ret=%d\n", r); if (r == 0) printf ("check=%d\n", _ESMUMPSorderCheck (&ordedat)); break;
    case 3 : r = loadstr ("0\n2\t3\n0\t5\t3\n0 2 1\n", &ordedat); printf ("load ret=%d\n", r); if (r == 0) printf ("check=%d\n", _ESMUMPSorderCheck (&ordedat)); break;
    case 4 : {
      INT     rangtab[1] = { 0 };
      ordedat.cblknbr = 0; ordedat.rangtab = rangtab; ordedat.permtab = malloc (0); ordedat.peritab = NULL;
      r = _ESMUMPSorderSave (&ordedat, stdout); printf ("save ret=%d\n", r);
      free (ordedat.permtab);
      return (r);
    }
    case 5 : {
      char    buf[256];
      FILE *  f;
      r = loadstr ("0\n2\t3\n0\t2\t3\n2 0 1\n", &ordedat); printf ("load ret=%d check=%d\n", r, _ESMUMPSorderCheck (&ordedat));
      f = fmemopen (buf, sizeof (buf), "w"); r = _ESMUMPSorderSave (&ordedat, f); fclose (f); printf ("save ret=%d\n%s", r, buf);
      _ESMUMPSorderExit (&ordedat); _ESMUMPSorderInit (&ordedat);
      r = loadstr (buf, &ordedat); printf ("reload ret=%d check=%d\n", r, _ESMUMPSorderCheck (&ordedat));
      break;
    }
    case 6 : {
      char    buf[4];
      FILE *  f;
      r = loadstr ("0\n2\t3\n0\t2\t3\n2 0 1\n", &ordedat);
      f = fmemopen (buf, 3, "w"); setvbuf (f, NULL, _IONBF, 0); /* Fails once the 3-byte buffer is full */
      r = _ESMUMPSorderSave (&ordedat, f); fclose (f); printf ("save on full stream ret=%d (should be != 0)\n", r);
      break;
    }
    default : return (3);
  }
  _ESMUMPSorderExit (&ordedat);
  return (0);
}
