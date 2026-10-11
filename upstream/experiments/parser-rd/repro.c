/* repro.c -- minimal characterization of the bison-parser crashes.
** For each argv string: parse with the stock bison parser, report whether
** parse returned non-NULL, then (guarded by argv order) save and exit,
** printing a breadcrumb before each step so a segfault names the phase.
*/

#define _GNU_SOURCE
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

#include "module.h"
#include "common.h"
#undef INTEGER
#undef DOUBLE
#include "parser.h"

extern StratTab             kgraphmapststratab;
Strat *                     stratParserParse (const StratTab * const, const char * const);

void errorPrint  (const char * const f, ...) { (void) f; }
void errorPrintW (const char * const f, ...) { (void) f; }

int
main (int argc, char * argv[])
{
  int                 i;

  for (i = 1; i < argc; i ++) {
    Strat *             s;

    fprintf (stderr, "parse   [%s] ...\n", argv[i]); fflush (stderr);
    s = stratParserParse (&kgraphmapststratab, argv[i]);
    fprintf (stderr, "  -> %s\n", (s != NULL) ? "ACCEPT" : "REJECT"); fflush (stderr);
    if (s == NULL)
      continue;
    fprintf (stderr, "exit    [%s] ...\n", argv[i]); fflush (stderr);
    stratExit (s);
    fprintf (stderr, "  -> exited cleanly\n"); fflush (stderr);
  }
  return (0);
}
