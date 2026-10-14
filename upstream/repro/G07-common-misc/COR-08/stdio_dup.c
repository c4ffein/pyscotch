/* COR-08: pending stdout data at fork time is flushed again by each child's exit().
** Usage: ./stdio_dup out1.gz out2.gz > log.txt ; then count the "HEADER" lines in log.txt.
** Expected: 1 line. Pristine fork-mode children: 1 + number of children. */
#include <stdio.h>
#include <stdlib.h>
#include "module.h"
#include "common.h"
#include "scotch.h"

static File                 filetab[2] = { { FILEMODEW }, { FILEMODEW } };

int
main (int argc, char * argv[])
{
  printf ("HEADER printed before fileBlockOpen\n");  /* Stays in the stdio buffer when stdout is a file */
  fileBlockInit (filetab, 2);
  fileBlockName (filetab, 0) = argv[1];
  fileBlockName (filetab, 1) = argv[2];
  if (fileBlockOpen (filetab, 2) != 0) {
    fprintf (stderr, "cannot open\n");
    return (1);
  }
  fprintf (fileBlockFile (filetab, 0), "one\n");
  fprintf (fileBlockFile (filetab, 1), "two\n");
  fileBlockClose (filetab, 2);
  printf ("TRAILER\n");
  return (0);
}
