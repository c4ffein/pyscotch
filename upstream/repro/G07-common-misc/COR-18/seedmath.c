/* COR-18: standalone re-implementation of the 7.0.16 and 7.0.17 per-rank
** seeding formulas (common_integer.c intRandReset/intRandSeed2) to look for
** state collisions between ranks, for a set of seeds. */
#include <stdio.h>
#include <stdint.h>

static void
state16 (uint64_t seedval, int procval, uint64_t * tab)  /* 7.0.16: ((seed | 1) * (proc + 1)) | 1 */
{
  uint64_t randval = (seedval | 1U) * ((uint64_t) procval + 1U);
  uint64_t s = (uint64_t) ((uint32_t) randval | 1U); /* 7.0.16 cast randval to INT (32-bit INT build) then | 1 */
  tab[0] = s ^ (s << 15); tab[1] = s ^ (s << 24);
}
static void
state17 (uint64_t seedval, int procval, uint64_t * tab)  /* 7.0.17: (2*seed+1)*(2*proc+1), then 2*x+1 */
{
  uint64_t randval = (seedval * 2U + 1U) * ((uint64_t) procval * 2U + 1U);
  uint64_t s = randval * 2U + 1U;
  tab[0] = s ^ (s << 15); tab[1] = s ^ (s << 24);
}

int
main (void)
{
  uint64_t seedtab[] = { 1, 0, 2, 3, 12345, 1760000000ULL };
  int seednum, p, q, c16 = 0, c17 = 0;
  for (seednum = 0; seednum < 6; seednum ++) {
    for (p = 0; p < 1024; p ++) {
      uint64_t a16[2], b16[2], a17[2], b17[2];
      state16 (seedtab[seednum], p, a16); state17 (seedtab[seednum], p, a17);
      for (q = p + 1; q < 1024; q ++) {
        state16 (seedtab[seednum], q, b16); state17 (seedtab[seednum], q, b17);
        if (a16[0] == b16[0] && a16[1] == b16[1]) { if (c16 ++ < 4) printf ("7.0.16 seed %llu: ranks %d and %d share a state\n", (unsigned long long) seedtab[seednum], p, q); }
        if (a17[0] == b17[0] && a17[1] == b17[1]) { if (c17 ++ < 4) printf ("7.0.17 seed %llu: ranks %d and %d share a state\n", (unsigned long long) seedtab[seednum], p, q); }
      }
    }
  }
  printf ("1024 ranks x 6 seeds: 7.0.16 collisions=%d, 7.0.17 collisions=%d\n", c16, c17);
  return (0);
}
