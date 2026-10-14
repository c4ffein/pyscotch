! Functional test of the PT-Scotch Fortran wrappers added or fixed by the G17 series
! (run with mpirun -np 2): scotchfdgraphstat (API-09, lower-case symbol), scotchfdgraphmapstat
! with its trailing ierr (API-11), scotchfdgraphfree, scotchfdgraphgrow, scotchfdmeshfree,
! scotchfdmapsizeof, scotchfdordersizeof (API-24).
program par_f
  use iso_c_binding
  use mpi
  implicit none
  interface
    subroutine exit_c (val) bind(c, name='exit')
      use, intrinsic :: iso_c_binding, only: c_int
      integer(c_int), value, intent(in) :: val
    end subroutine exit_c
  end interface
  include 'ptscotchf.h'
  doubleprecision :: grafdat(SCOTCH_DGRAPHDIM), meshdat(SCOTCH_DMESHDIM), mappdat(SCOTCH_DMAPDIM)
  doubleprecision :: archdat(SCOTCH_ARCHDIM), stradat(SCOTCH_STRATDIM)
  integer(SCOTCH_NUMSIZE) :: velomin, velomax, velosum, degrmin, degrmax, edlomin, edlomax, edlosum
  doubleprecision :: veloavg, velodlt, degravg, degrdlt, edloavg, edlodlt
  integer(SCOTCH_NUMSIZE) :: tgtnbr, mapnbr, mapmin, mapmax, ngbsum, ngbmin, ngbmax, cdstmax, cdsttab(256)
  integer(SCOTCH_NUMSIZE) :: cmlosum, cmdisum, cmexsum
  doubleprecision :: mapavg, mapdlt
  integer(SCOTCH_NUMSIZE) :: indxtab(1), baseval, vertglbnbr, vertlocnbr, vertlocmax, vertgstnbr
  integer(SCOTCH_NUMSIZE) :: edgeglbnbr, edgelocnbr, edgelocsiz
  integer(SCOTCH_IDXSIZE) :: vertlocidx, vendlocidx, velolocidx, vlbllocidx, edgelocidx, edgegstidx, edlolocidx
  integer(SCOTCH_NUMSIZE), allocatable :: partgsttab(:), termloctab(:), seedloctab(:)
  integer :: ierr, mpierr, rank, comm, sizeval, i

  call MPI_Init (mpierr)
  call MPI_Comm_rank (MPI_COMM_WORLD, rank, mpierr)
  comm = MPI_COMM_WORLD

  call scotchfdgraphinit (grafdat, comm, ierr)
  call check (ierr, "dgraphinit")
  call scotchfdgraphbuildgrid3d (grafdat, 0_SCOTCH_NUMSIZE, 4_SCOTCH_NUMSIZE, 4_SCOTCH_NUMSIZE, 1_SCOTCH_NUMSIZE, &
                                 1_SCOTCH_NUMSIZE, 0_SCOTCH_NUMSIZE, ierr)
  call check (ierr, "dgraphbuildgrid3d")
  call scotchfdgraphghst (grafdat, ierr)
  call check (ierr, "dgraphghst")
  call scotchfdgraphdata (grafdat, indxtab, baseval, vertglbnbr, vertlocnbr, vertlocmax, vertgstnbr, &
                          vertlocidx, vendlocidx, velolocidx, vlbllocidx, edgeglbnbr, edgelocnbr, edgelocsiz, &
                          edgelocidx, edgegstidx, edlolocidx, comm)

  ! API-09: scotchfdgraphstat
  ierr = -77
  call scotchfdgraphstat (grafdat, velomin, velomax, velosum, veloavg, velodlt, degrmin, degrmax, degravg, degrdlt, &
                          edlomin, edlomax, edlosum, edloavg, edlodlt, ierr)
  call check (ierr, "dgraphstat")
  if (velosum /= 16) then
    print *, "ERROR: dgraphstat velosum=", velosum
    call exit_c (1)
  end if

  ! API-24: scotchfdgraphgrow from one local seed
  allocate (partgsttab(vertgstnbr))
  allocate (seedloctab(vertlocnbr))                 ! Used as a queue by SCOTCH_dgraphGrow, as in test_scotch_dgraph_grow.c
  partgsttab(:) = -1
  seedloctab(1) = baseval
  partgsttab(1) = 0
  call scotchfdgraphgrow (grafdat, 1_SCOTCH_NUMSIZE, seedloctab, 2_SCOTCH_NUMSIZE, partgsttab, ierr)
  call check (ierr, "dgraphgrow")
  do i = 1, vertlocnbr
    if ((partgsttab(i) < -1) .or. (partgsttab(i) >= 1)) then
      print *, "ERROR: dgraphgrow invalid part value ", partgsttab(i)
      call exit_c (1)
    end if
  end do
  if (partgsttab(1) /= 0) then
    print *, "ERROR: dgraphgrow seed not in its own region"
    call exit_c (1)
  end if
  deallocate (partgsttab)
  deallocate (seedloctab)

  ! API-11: scotchfdgraphmapstat with trailing ierr
  call scotchfarchinit (archdat, ierr)
  call scotchfarchcmplt (archdat, 2_SCOTCH_NUMSIZE, ierr)
  call check (ierr, "archcmplt")
  call scotchfstratinit (stradat, ierr)
  allocate (termloctab(vertlocnbr))
  call scotchfdgraphmapinit (grafdat, mappdat, archdat, termloctab, ierr)
  call check (ierr, "dgraphmapinit")
  call scotchfdgraphmapcompute (grafdat, mappdat, stradat, ierr)
  call check (ierr, "dgraphmapcompute")
  ierr = -77
  call scotchfdgraphmapstat (grafdat, mappdat, tgtnbr, mapnbr, mapmin, mapmax, mapavg, mapdlt, ngbsum, ngbmin, ngbmax, &
                             cdstmax, cdsttab, cmlosum, cmdisum, cmexsum, ierr)
  if (ierr /= 0) then
    print *, "ERROR: dgraphmapstat ierr=", ierr, " (-77 means never written)"
    call exit_c (1)
  end if
  if ((tgtnbr /= 2) .or. (mapmin > mapmax)) then
    print *, "ERROR: dgraphmapstat tgtnbr=", tgtnbr, " mapmin=", mapmin, " mapmax=", mapmax
    call exit_c (1)
  end if
  call scotchfdgraphmapexit (grafdat, mappdat)
  deallocate (termloctab)
  call scotchfstratexit (stradat)
  call scotchfarchexit (archdat)

  ! API-24: scotchfdgraphfree, then rebuild and exit
  call scotchfdgraphfree (grafdat)
  call scotchfdgraphbuildgrid3d (grafdat, 0_SCOTCH_NUMSIZE, 2_SCOTCH_NUMSIZE, 2_SCOTCH_NUMSIZE, 1_SCOTCH_NUMSIZE, &
                                 1_SCOTCH_NUMSIZE, 0_SCOTCH_NUMSIZE, ierr)
  call check (ierr, "dgraphbuildgrid3d after dgraphfree")
  call scotchfdgraphexit (grafdat)

  ! API-24: scotchfdmeshfree
  call scotchfdmeshinit (meshdat, comm, ierr)
  call check (ierr, "dmeshinit")
  call scotchfdmeshfree (meshdat)
  call scotchfdmeshexit (meshdat)

  ! API-24: the two missing *sizeof routines
  call scotchfdmapsizeof (sizeval)
  if (sizeval /= 8 * SCOTCH_DMAPDIM) then   ! Sizeof routines return bytes, *DIM count doubles
    print *, "ERROR: dmapsizeof=", sizeval, " SCOTCH_DMAPDIM=", SCOTCH_DMAPDIM
    call exit_c (1)
  end if
  call scotchfdordersizeof (sizeval)
  if (sizeval /= 8 * SCOTCH_DORDERDIM) then
    print *, "ERROR: dordersizeof=", sizeval, " SCOTCH_DORDERDIM=", SCOTCH_DORDERDIM
    call exit_c (1)
  end if

  if (rank == 0) print *, "par_f: OK"
  call MPI_Finalize (mpierr)

contains

  subroutine check (ierr, what)
    integer, intent(in) :: ierr
    character(*), intent(in) :: what
    if (ierr /= 0) then
      print *, "ERROR: ", what, " ierr=", ierr
      call exit_c (1)
    end if
  end subroutine check

end program par_f
