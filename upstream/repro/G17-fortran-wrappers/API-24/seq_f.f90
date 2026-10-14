! Functional test of the sequential Fortran wrappers added or fixed by the G17 series:
! scotchfarchbuild0, scotchfarchbuild2, scotchfarchltleaf, scotchfgraphorderload,
! scotchfmeshstat, scotchfstratsizeof, scotchfmapsizeof, scotchfordersizeof, and
! scotchfarchsize (API-13: full-width SCOTCH_Num result).
! Prints "SIZEOF ..." and "MESHSTAT ..." lines to be compared with seq_c's output.
program seq_f
  use iso_c_binding
  implicit none
  interface
    subroutine exit_c (val) bind(c, name='exit')
      use, intrinsic :: iso_c_binding, only: c_int
      integer(c_int), value, intent(in) :: val
    end subroutine exit_c
  end interface
  include 'scotchf.h'
  doubleprecision :: archdat(SCOTCH_ARCHDIM), grafdat(SCOTCH_GRAPHDIM), stradat(SCOTCH_STRATDIM)
  doubleprecision :: meshdat(SCOTCH_MESHDIM), ordedat(SCOTCH_ORDERDIM), orde2dat(SCOTCH_ORDERDIM)
  integer(SCOTCH_NUMSIZE) :: verttab(9) = [ 0, 2, 4, 6, 8, 10, 12, 14, 16 ]
  integer(SCOTCH_NUMSIZE) :: edgetab(16) = [ 7, 1, 0, 2, 1, 3, 2, 4, 3, 5, 4, 6, 5, 7, 6, 0 ]
  integer(SCOTCH_NUMSIZE) :: listtab(8) = [ 0, 1, 2, 3, 4, 5, 6, 7 ]
  integer(SCOTCH_NUMSIZE) :: sizetab(2) = [ 2, 3 ], linktab(2) = [ 2, 1 ]
  integer(SCOTCH_NUMSIZE) :: permtab(6) = [ 1, 0, 3, 2, 5, 4 ]
  integer(SCOTCH_NUMSIZE) :: mverttab(12) = [ 1, 5, 9, 13, 14, 16, 18, 20, 21, 22, 23, 25 ]
  integer(SCOTCH_NUMSIZE) :: medgetab(24) = [ 5, 11, 7, 6, 10, 5, 11, 4, 8, 9, 6, 7, 2, 2, 1, 1, 3, 1, 3, 3, 3, 2, 2, 1 ]
  integer(SCOTCH_NUMSIZE) :: operm(8), operi(8), orang(9), otree(8), cblknbr
  integer(SCOTCH_NUMSIZE) :: operm2(8), operi2(8), orang2(9), otree2(8), cblknbr2
  integer(SCOTCH_NUMSIZE) :: archnbr
  integer(SCOTCH_NUMSIZE) :: vnlomin, vnlomax, vnlosum, edegmin, edegmax, ndegmin, ndegmax
  doubleprecision :: vnloavg, vnlodlt, edegavg, edegdlt, ndegavg, ndegdlt
  integer :: ierr, sizeval, fildes, i, fnum

  call scotchfstratinit (stradat, ierr)
  call scotchfgraphinit (grafdat, ierr)
  call scotchfgraphbuild (grafdat, 0_SCOTCH_NUMSIZE, 8_SCOTCH_NUMSIZE, verttab, verttab, verttab, verttab, &
                          16_SCOTCH_NUMSIZE, edgetab, edgetab, ierr)
  call check (ierr, "graphbuild")
  call scotchfgraphcheck (grafdat, ierr)
  call check (ierr, "graphcheck")

  ! scotchfarchbuild2 + scotchfarchsize (API-13: sentinel with all bits set)
  call scotchfarchinit (archdat, ierr)
  call scotchfarchbuild2 (archdat, grafdat, 8_SCOTCH_NUMSIZE, listtab, ierr)
  call check (ierr, "archbuild2")
  archnbr = -1
  call scotchfarchsize (archdat, archnbr)
  if (archnbr /= 8) then
    print *, "ERROR: archsize after archbuild2: ", archnbr
    call exit_c (1)
  end if
  call scotchfarchexit (archdat)

  ! scotchfarchbuild0 with the default (empty) strategy
  call scotchfarchinit (archdat, ierr)
  call scotchfarchbuild0 (archdat, grafdat, 8_SCOTCH_NUMSIZE, listtab, stradat, ierr)
  call check (ierr, "archbuild0")
  archnbr = -1
  call scotchfarchsize (archdat, archnbr)
  if (archnbr /= 8) then
    print *, "ERROR: archsize after archbuild0: ", archnbr
    call exit_c (1)
  end if
  call scotchfarchexit (archdat)
  call scotchfstratexit (stradat)

  ! scotchfarchltleaf
  call scotchfarchinit (archdat, ierr)
  call scotchfarchltleaf (archdat, 2_SCOTCH_NUMSIZE, sizetab, linktab, 6_SCOTCH_NUMSIZE, permtab, ierr)
  call check (ierr, "archltleaf")
  archnbr = -1
  call scotchfarchsize (archdat, archnbr)
  if (archnbr /= 6) then
    print *, "ERROR: archsize after archltleaf: ", archnbr
    call exit_c (1)
  end if
  call scotchfarchexit (archdat)

  ! scotchfgraphorderload: save an ordering, load it back, check it
  call scotchfstratinit (stradat, ierr)
  call scotchfgraphorderinit (grafdat, ordedat, operm, operi, cblknbr, orang, otree, ierr)
  call check (ierr, "graphorderinit")
  call scotchfgraphordercompute (grafdat, ordedat, stradat, ierr)
  call check (ierr, "graphordercompute")
  open (unit = 10, file = 'seq_f.ord', status = 'replace', action = 'write')
  fildes = fnum (10)
  call scotchfgraphordersave (grafdat, ordedat, fildes, ierr)
  call check (ierr, "graphordersave")
  close (10)
  call scotchfgraphorderinit (grafdat, orde2dat, operm2, operi2, cblknbr2, orang2, otree2, ierr)
  call check (ierr, "graphorderinit (2)")
  open (unit = 10, file = 'seq_f.ord', status = 'old', action = 'read')
  fildes = fnum (10)
  call scotchfgraphorderload (grafdat, orde2dat, fildes, ierr)
  call check (ierr, "graphorderload")
  close (10)
  call scotchfgraphordercheck (grafdat, orde2dat, ierr)
  call check (ierr, "graphordercheck after load")
  do i = 1, 8
    if (operm2(i) /= operm(i)) then
      print *, "ERROR: loaded permutation differs at ", i, operm(i), operm2(i)
      call exit_c (1)
    end if
  end do
  call scotchfgraphorderexit (grafdat, orde2dat)
  call scotchfgraphorderexit (grafdat, ordedat)
  call scotchfstratexit (stradat)
  call scotchfgraphexit (grafdat)

  ! scotchfmeshstat on the mesh of test_scotch_mesh_build_f
  call scotchfmeshinit (meshdat, ierr)
  call scotchfmeshbuild (meshdat, 1_SCOTCH_NUMSIZE, 4_SCOTCH_NUMSIZE, 3_SCOTCH_NUMSIZE, 8_SCOTCH_NUMSIZE, &
                         mverttab, mverttab, mverttab, mverttab, mverttab, 24_SCOTCH_NUMSIZE, medgetab, ierr)
  call check (ierr, "meshbuild")
  call scotchfmeshcheck (meshdat, ierr)
  call check (ierr, "meshcheck")
  call scotchfmeshstat (meshdat, vnlomin, vnlomax, vnlosum, vnloavg, vnlodlt, edegmin, edegmax, edegavg, edegdlt, &
                        ndegmin, ndegmax, ndegavg, ndegdlt)
  write (*, '(A,7(1X,I0),6(1X,F10.4))') "MESHSTAT", vnlomin, vnlomax, vnlosum, edegmin, edegmax, ndegmin, ndegmax, &
                                         vnloavg, vnlodlt, edegavg, edegdlt, ndegavg, ndegdlt
  call scotchfmeshexit (meshdat)

  ! The three missing *sizeof routines
  call scotchfstratsizeof (sizeval)
  write (*, '(A,1X,I0)') "SIZEOF strat", sizeval
  call scotchfmapsizeof (sizeval)
  write (*, '(A,1X,I0)') "SIZEOF map", sizeval
  call scotchfordersizeof (sizeval)
  write (*, '(A,1X,I0)') "SIZEOF order", sizeval

  print *, "seq_f: OK"

contains

  subroutine check (ierr, what)
    integer, intent(in) :: ierr
    character(*), intent(in) :: what
    if (ierr /= 0) then
      print *, "ERROR: ", what, " ierr=", ierr
      call exit_c (1)
    end if
  end subroutine check

end program seq_f
