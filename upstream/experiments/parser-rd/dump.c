/* dump.c -- print the canonical saved forms of upstream's own generated
** strategies (SCOTCH_stratGraphMapBuild / SCOTCH_stratGraphOrderBuild over
** the flag space), one per line. These are the richest realistic seeds for
** the differential fuzzer: they exercise conditions, selections, nesting
** and every default method. Built against the public API only.
*/

#include <stdio.h>
#include <stdint.h>

#include "scotch.h"

static void
dumpMap (
const SCOTCH_Num            flagval,
const SCOTCH_Num            partnbr,
const double                kbalval)
{
  SCOTCH_Strat        stradat;

  SCOTCH_stratInit (&stradat);
  if (SCOTCH_stratGraphMapBuild (&stradat, flagval, partnbr, kbalval) == 0) {
    SCOTCH_stratSave (&stradat, stdout);
    printf ("\n");
  }
  SCOTCH_stratExit (&stradat);
}

static void
dumpOrder (
const SCOTCH_Num            flagval,
const SCOTCH_Num            levlnbr,
const double                balrat)
{
  SCOTCH_Strat        stradat;

  SCOTCH_stratInit (&stradat);
  if (SCOTCH_stratGraphOrderBuild (&stradat, flagval, levlnbr, balrat) == 0) {
    SCOTCH_stratSave (&stradat, stdout);
    printf ("\n");
  }
  SCOTCH_stratExit (&stradat);
}

int
main (void)
{
  static const SCOTCH_Num mapflagtab[] = {
    SCOTCH_STRATDEFAULT, SCOTCH_STRATQUALITY, SCOTCH_STRATSPEED,
    SCOTCH_STRATBALANCE, SCOTCH_STRATSAFETY,  SCOTCH_STRATRECURSIVE,
  };
  static const SCOTCH_Num ordflagtab[] = {
    SCOTCH_STRATDEFAULT, SCOTCH_STRATQUALITY, SCOTCH_STRATSPEED,
    SCOTCH_STRATBALANCE, SCOTCH_STRATSAFETY,  SCOTCH_STRATLEVELMAX,
    SCOTCH_STRATLEVELMIN, SCOTCH_STRATLEAFSIMPLE, SCOTCH_STRATSEPASIMPLE,
  };
  size_t              i;

  for (i = 0; i < sizeof (mapflagtab) / sizeof (mapflagtab[0]); i ++) {
    dumpMap (mapflagtab[i], 2,  0.01);
    dumpMap (mapflagtab[i], 64, 0.1);
  }
  for (i = 0; i < sizeof (ordflagtab) / sizeof (ordflagtab[0]); i ++) {
    dumpOrder (ordflagtab[i], 0, 0.1);
    dumpOrder (ordflagtab[i], 3, 0.2);
  }
  return (0);
}
