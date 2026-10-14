! Call the Fortran interface of SCOTCH_contextOptionParse() and check option values
program optf
  implicit none
  include "scotchf.h"
  doubleprecision     contdat(SCOTCH_CONTEXTDIM)
  integer             ierr
  integer (kind=SCOTCH_NUMSIZE) :: deteval, rafival

  call scotchfcontextinit (contdat, ierr)
  if (ierr /= 0) stop 1
  call scotchfcontextoptionparse (contdat, "d", ierr)
  print *, "parse d: ierr =", ierr
  call scotchfcontextoptiongetnum (contdat, SCOTCH_OPTIONNUMDETERMINISTIC, deteval, ierr)
  call scotchfcontextoptiongetnum (contdat, SCOTCH_OPTIONNUMRANDOMFIXEDSEED, rafival, ierr)
  print *, "deterministic =", deteval, " fixedseed =", rafival
  call scotchfcontextoptionparse (contdat, "x", ierr)
  print *, "parse x: ierr =", ierr, " (expect 1)"
  call scotchfcontextexit (contdat)
  if (deteval /= 1 .or. rafival /= 1) stop 2
end program optf
