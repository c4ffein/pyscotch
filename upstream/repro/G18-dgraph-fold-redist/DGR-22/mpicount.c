/* DGR-22 boundary demo: a 64-bit Gnum count narrowed to an MPI int count */
#include <stdio.h>
#include <limits.h>
#include <mpi.h>
int main (int argc, char * argv[]) {
  long cnt; int icnt, rc, len; char msg[MPI_MAX_ERROR_STRING]; MPI_Request req; static long buf[4];
  MPI_Init (&argc, &argv);
  MPI_Comm_set_errhandler (MPI_COMM_WORLD, MPI_ERRORS_RETURN);
  for (cnt = (long) INT_MAX; cnt <= (long) INT_MAX + 2; cnt ++) {
    icnt = (int) cnt;                             /* What MPI_Isend (buf, cnt, ...) does implicitly */
    rc = MPI_Isend (buf, icnt, MPI_LONG, 0, 0, MPI_COMM_WORLD, &req);
    MPI_Error_string (rc, msg, &len);
    printf ("Gnum count %ld -> int count %d : MPI_Isend rc=%d (%s)\n", cnt, icnt, rc, msg);
    if (rc == MPI_SUCCESS) MPI_Cancel (&req), MPI_Request_free (&req);
  }
  cnt = 4294967300L; icnt = (int) cnt;            /* 2^32 + 4: wraps to a small positive count: silent truncation */
  printf ("Gnum count %ld -> int count %d : silently sends %d elements\n", cnt, icnt, icnt);
  MPI_Finalize (); return 0; }
