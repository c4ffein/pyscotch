/* Exercise the architecture builders with the argument sets of the review and the first pass */
#include <stdio.h>
#include <stdlib.h>
#include "scotch.h"
#ifndef HAVE_LTLEAF_PROTO
int SCOTCH_archLtleaf (SCOTCH_Arch * const, const SCOTCH_Num, const SCOTCH_Num * const, const SCOTCH_Num * const, const SCOTCH_Num, const SCOTCH_Num * const);
#endif
int main (int argc, char * argv[]) {
  SCOTCH_Arch a; int r = -1; int w = atoi (argv[1]);
  SCOTCH_errorProg (argv[0]);
  setvbuf (stdout, NULL, _IONBF, 0);
  SCOTCH_archInit (&a);
  if (w == 0) { SCOTCH_Num sz[1] = {2}, lk[1] = {1}, pm[2] = {5, 0}; r = SCOTCH_archLtleaf (&a, 1, sz, lk, 2, pm); printf ("archLtleaf perm{5,0} r=%d\n", r); }
  if (w == 1) { SCOTCH_Num sz[1] = {4}, lk[1] = {1}, pm[4] = {0, 0, 1, 2}; r = SCOTCH_archLtleaf (&a, 1, sz, lk, 4, pm); printf ("archLtleaf dup perm r=%d\n", r); if (r == 0) { SCOTCH_ArchDom d; int i; for (i = 0; i < 4; i ++) { SCOTCH_archDomTerm (&a, &d, i); printf (" term %d -> domnum %ld\n", i, (long) SCOTCH_archDomNum (&a, &d)); } } }
  if (w == 2) { SCOTCH_Num sz[1] = {4}, lk[1] = {1}, pm[3] = {2, 1, 0}; r = SCOTCH_archLtleaf (&a, 1, sz, lk, 3, pm); printf ("archLtleaf permnbr 3 on size 4 r=%d\n", r); if (r == 0) { SCOTCH_ArchDom d; int i; for (i = 0; i < 4; i ++) { SCOTCH_archDomTerm (&a, &d, i); printf (" term %d -> domnum %ld\n", i, (long) SCOTCH_archDomNum (&a, &d)); } } }
  if (w == 3) { r = SCOTCH_archHcub (&a, atoi (argv[2])); printf ("archHcub(%s) r=%d size=%ld\n", argv[2], r, (long) SCOTCH_archSize (&a)); }
  if (w == 4) { SCOTCH_Num sz[2] = {0, -3}, lk[2] = {0, 0}; r = SCOTCH_archTleaf (&a, 2, sz, lk); printf ("archTleaf sizes{0,-3} r=%d size=%ld\n", r, (long) SCOTCH_archSize (&a)); }
  if (w == 5) { r = SCOTCH_archTleaf (&a, -1, NULL, NULL); printf ("archTleaf(-1) r=%d\n", r); }
  if (w == 6) { r = SCOTCH_archTleaf (&a, 0, NULL, NULL); printf ("archTleaf(0) r=%d size=%ld\n", r, (long) SCOTCH_archSize (&a)); }
  if (w == 7) { SCOTCH_Num sz[2] = {65536, 65536}, lk[2] = {1, 1}; r = SCOTCH_archTleaf (&a, 2, sz, lk); printf ("archTleaf 65536x65536 r=%d size=%ld\n", r, (long) SCOTCH_archSize (&a)); }
  if (w == 8) { SCOTCH_Num sz[2] = {2, 4}, lk[2] = {3, 1}, pm[8] = {0, 2, 4, 6, 1, 3, 5, 7}; r = SCOTCH_archLtleaf (&a, 2, sz, lk, 8, pm); printf ("archLtleaf valid r=%d size=%ld\n", r, (long) SCOTCH_archSize (&a)); if (r == 0) { FILE * f = tmpfile (); char buf[256]; SCOTCH_archSave (&a, f); rewind (f); while (fgets (buf, 256, f)) fputs (buf, stdout); fclose (f); } }
  if (w == 9) { SCOTCH_Num sz[2] = {2, 4}, lk[2] = {3, 1}, pm[8] = {0, 2, 4, 6, 1, 3, 5, 7}; r = SCOTCH_archLtleaf (&a, 2, sz, lk, 8, pm); printf ("archLtleaf (under malloc failure) r=%d\n", r); }
  if (w == 10) { SCOTCH_Num sz[2] = {2, 4}, lk[2] = {3, 1}; r = SCOTCH_archTleaf (&a, 2, sz, lk); printf ("archTleaf (under malloc failure) r=%d\n", r); }
  SCOTCH_archExit (&a);
  printf ("exit ok\n");
  return (0);
}
