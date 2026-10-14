/* Spawn 4 threads on explicit logical cores {4,5,6,7} and {0,1,2,3}; print every thread's affinity from /proc */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sched.h>
#include <unistd.h>
#include <scotch.h>

static
void
tasksPrint (
const char * const          lablstr)
{
  DIR *               dirptr;
  struct dirent *     entptr;

  printf ("%s\n", lablstr);
  dirptr = opendir ("/proc/self/task");
  while ((entptr = readdir (dirptr)) != NULL) {
    char                namestr[256];
    char                linestr[256];
    FILE *              fileptr;

    if (entptr->d_name[0] == '.')
      continue;
    sprintf (namestr, "/proc/self/task/%s/status", entptr->d_name);
    if ((fileptr = fopen (namestr, "r")) == NULL)
      continue;
    while (fgets (linestr, sizeof (linestr), fileptr) != NULL)
      if (strncmp (linestr, "Cpus_allowed_list:", 18) == 0)
        printf ("  task %s %s", entptr->d_name, linestr);
    fclose (fileptr);
  }
  closedir (dirptr);
}

int
main (
int                 argc,
char *              argv[])
{
  SCOTCH_Context *    contptr;
  int                 coretab[4];
  int                 i;
  int                 o;

  tasksPrint ("process mask before spawn");
  for (i = 0; i < 4; i ++)
    coretab[i] = atoi (argv[1 + i]);

  contptr = SCOTCH_contextAlloc ();
  SCOTCH_contextInit (contptr);
  o = SCOTCH_contextThreadSpawn (contptr, 4, coretab);
  printf ("spawn returned %d\n", o);
  usleep (100000);
  tasksPrint ("thread masks after spawn");
  SCOTCH_contextExit (contptr);
  usleep (100000);
  tasksPrint ("after exit");
  free (contptr);
  return (0);
}
