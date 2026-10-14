! Link test: the thirteen Fortran routines documented in the manuals but absent from the library.
program missing_f
  use mpi
  implicit none
  include 'ptscotchf.h'
  doubleprecision :: archdat(SCOTCH_ARCHDIM), grafdat(SCOTCH_GRAPHDIM), stradat(SCOTCH_STRATDIM)
  doubleprecision :: meshdat(SCOTCH_MESHDIM), ordedat(SCOTCH_ORDERDIM)
  doubleprecision :: dgrfdat(SCOTCH_DGRAPHDIM), dmshdat(SCOTCH_DMESHDIM)
  integer(SCOTCH_NUMSIZE) :: listtab(2), sizetab(2), linktab(2), permtab(2), seedtab(1), parttab(8)
  integer(SCOTCH_NUMSIZE) :: vnlomin, vnlomax, vnlosum, edegmin, edegmax, ndegmin, ndegmax
  doubleprecision :: vnloavg, vnlodlt, edegavg, edegdlt, ndegavg, ndegdlt
  integer :: ierr, sizeval, fildes, mpierr
  call MPI_Init (mpierr)
  call scotchfarchbuild0 (archdat, grafdat, 2_SCOTCH_NUMSIZE, listtab, stradat, ierr)
  call scotchfarchbuild2 (archdat, grafdat, 2_SCOTCH_NUMSIZE, listtab, ierr)
  call scotchfarchltleaf (archdat, 2_SCOTCH_NUMSIZE, sizetab, linktab, 2_SCOTCH_NUMSIZE, permtab, ierr)
  call scotchfgraphorderload (grafdat, ordedat, fildes, ierr)
  call scotchfmeshstat (meshdat, vnlomin, vnlomax, vnlosum, vnloavg, vnlodlt, edegmin, edegmax, edegavg, edegdlt, &
                        ndegmin, ndegmax, ndegavg, ndegdlt)
  call scotchfstratsizeof (sizeval)
  call scotchfmapsizeof (sizeval)
  call scotchfordersizeof (sizeval)
  call scotchfdgraphfree (dgrfdat)
  call scotchfdgraphgrow (dgrfdat, 1_SCOTCH_NUMSIZE, seedtab, 1_SCOTCH_NUMSIZE, parttab, ierr)
  call scotchfdmeshfree (dmshdat)
  call scotchfdmapsizeof (sizeval)
  call scotchfdordersizeof (sizeval)
  call MPI_Finalize (mpierr)
end program missing_f
