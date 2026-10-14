! Link test: a Fortran caller of the documented scotchfdgraphstat routine.
program stat_f
  use mpi
  implicit none
  include 'ptscotchf.h'
  doubleprecision :: grafdat(SCOTCH_DGRAPHDIM)
  integer(SCOTCH_NUMSIZE) :: velomin, velomax, velosum, degrmin, degrmax, edlomin, edlomax, edlosum
  doubleprecision :: veloavg, velodlt, degravg, degrdlt, edloavg, edlodlt
  integer :: ierr, mpierr
  call MPI_Init (mpierr)
  call scotchfdgraphinit (grafdat, MPI_COMM_WORLD, ierr)
  if (ierr /= 0) stop 1
  call scotchfdgraphbuildgrid3d (grafdat, 0_SCOTCH_NUMSIZE, 4_SCOTCH_NUMSIZE, 4_SCOTCH_NUMSIZE, 1_SCOTCH_NUMSIZE, 1_SCOTCH_NUMSIZE, 0_SCOTCH_NUMSIZE, ierr)
  if (ierr /= 0) stop 2
  call scotchfdgraphstat (grafdat, velomin, velomax, velosum, veloavg, velodlt, degrmin, degrmax, degravg, degrdlt, &
                          edlomin, edlomax, edlosum, edloavg, edlodlt, ierr)
  if (ierr /= 0) stop 3
  print *, "dgraphstat: velosum=", velosum, " degrmax=", degrmax
  call scotchfdgraphexit (grafdat)
  call MPI_Finalize (mpierr)
end program stat_f
