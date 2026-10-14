/* Pin the calling thread, import a 2-thread pool into a context, destroy the context, show the affinity mask */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <sched.h>
#include <scotch.h>

static SCOTCH_Context *     contptr;

static
void
maskPrint (
const char * const          lablstr)
{
  cpu_set_t           cpusdat;
  int                 cpunum;

  sched_getaffinity (0, sizeof (cpu_set_t), &cpusdat);
  printf ("%s: count=%d cpus:", lablstr, CPU_COUNT (&cpusdat));
  for (cpunum = 0; cpunum < 64; cpunum ++)
    if (CPU_ISSET (cpunum, &cpusdat))
      printf (" %d", cpunum);
  printf ("\n");
}

static
void *
slaveRun (
void *                      dataptr)
{
  SCOTCH_contextThreadImport2 (contptr, 1);
  return (NULL);
}

int
main (
int                 argc,
char *              argv[])
{
  pthread_t           thidval;
  cpu_set_t           cpusdat;

  CPU_ZERO (&cpusdat);                            /* Pin harness thread to CPU 1 */
  CPU_SET  (1, &cpusdat);
  if (sched_setaffinity (0, sizeof (cpu_set_t), &cpusdat) != 0) {
    printf ("cannot pin\n");
    return (2);
  }
  maskPrint ("before import");

  contptr = SCOTCH_contextAlloc ();
  SCOTCH_contextInit (contptr);
  SCOTCH_contextThreadImport1 (contptr, 2);
  pthread_create (&thidval, NULL, slaveRun, NULL);
  SCOTCH_contextThreadImport2 (contptr, 0);
  maskPrint ("after import");
  SCOTCH_contextExit (contptr);
  pthread_join (thidval, NULL);
  free (contptr);
  maskPrint ("after exit  ");

  sched_getaffinity (0, sizeof (cpu_set_t), &cpusdat);
  return ((CPU_COUNT (&cpusdat) == 1) && CPU_ISSET (1, &cpusdat)) ? 0 : 1;
}
