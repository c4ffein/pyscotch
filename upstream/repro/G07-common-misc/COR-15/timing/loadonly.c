/* COR-15 timing: load a graph file N times with SCOTCH_graphLoad() and print the wall time. */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <scotch.h>

int
main (int argc, char * argv[])
{
  SCOTCH_Graph        grafdat;
  FILE *              stream;
  struct timespec     t0, t1;
  int                 i, n = (argc > 2) ? atoi (argv[2]) : 3;
  double              best = 1e9;

  for (i = 0; i < n; i ++) {
    double d;
    SCOTCH_graphInit (&grafdat);
    stream = fopen (argv[1], "r");
    clock_gettime (CLOCK_MONOTONIC, &t0);
    if (SCOTCH_graphLoad (&grafdat, stream, -1, 0) != 0) { fprintf (stderr, "load failed\n"); return (1); }
    clock_gettime (CLOCK_MONOTONIC, &t1);
    fclose (stream);
    SCOTCH_graphExit (&grafdat);
    d = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);
    if (d < best) best = d;
    printf ("run %d: %.3f s\n", i, d);
  }
  printf ("best of %d: %.3f s\n", n, best);
  return (0);
}
