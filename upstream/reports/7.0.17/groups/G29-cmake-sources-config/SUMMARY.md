# G29-cmake-sources-config — SUMMARY (series based on the combined series: base-combined = v7.0.17 + 142 commits; 11 commits on top)

BLD-01   still-present  ran        high    -> patches/0001 (+0002, 0003, 0004 cleanups; 0005 ci/check_sources.sh)
BLD-02   still-present  ran        medium  -> patches/0006
BLD-12   still-present  ran        medium  -> patches/0007
BLD-13   still-present  partly-run low     -> patches/0008 (README.md + doc/src/handson/h_c.tex updated; PDFs not regenerated)
BLD-24   still-present  ran        low     -> patches/0009
BLD-25   still-present  ran        info    -> patches/0010
BLD-06   still-present  ran        low     -> patches/0011
PS-BLD-2 still-present  ran        low     -> patches/0011
PS2-G29-1 dead common_error.c in CMake libscotch (un-prefixed errorPrint exported)      low    -> patches/0002
PS2-G29-2 symbol_fax.c compiled standalone in CMake libesmumps (un-prefixed symbolFax)  low    -> patches/0003
PS2-G29-3 misspelt rules in src/libscotch/Makefile (arch_vcpmlt, library_arch_dom)       low    -> patches/0004
PS2-G29-4 suffixed CMake build with ENABLE_TESTS=ON fails to link test_scotch_mesh_build_f medium -> no patch (src/check template, G30)

Three facts that matter
1. cmake 4.4.4 exists on this box (uv cache wheel, /home/dev/.cache/uv/archive-v0/AYBj08OZ5Y7UxitH/cmake/data/bin): every item was RUN, not read.
   All 8 leads confirmed; CI-flag builds of the patched tree: 32-bit and INTSIZE=64 (ctest 181/181 each), suffixed, BUILD_LIBESMUMPS=OFF
   and static (find_package consumer OK on all installs). Makefile builds 32/64-bit: 0 warnings; sequential `make check`: no error (ptcheck not run).
2. The CMake-built libScotch was worse than the review said: besides the 5 missing files it links the dead common_error.c and exports
   un-prefixed errorPrint/errorPrintW/errorProg; libesmumps exports an un-prefixed symbolFax. The new ci/check_sources.sh finds all of it.
3. BLD-12 is a real race (9/10 parallel `make all` runs generated metis.h twice) but is invisible to `make -jN target1 target2`
   (CMake's top-level Makefile is .NOTPARALLEL): a naive reproduction says "no race".

Not done / caveats
- BLD-13: no CMake 3.10-3.17 here; version facts come from the cmake binary's own docs except `-E cat` (3.18, from memory). doc PDFs not rebuilt.
- BLD-24 FreeBSD branch not executed (grep evidence only). stylecheck.py is a C checker: its hits on CMake files are pre-existing idiom.
- PS2-G29-4 left to G30 (src/check/test_scotch_mesh_build_f.f90.in calls scotchfmeshinit literally; the metis template uses the name macro).
- alt/BLD-01-c (CMake parses the Makefile) and alt/BLD-13-b (floor 3.14, cmake -P concatenation) are working prototypes, configure/partly built.

For G30 (CI): add `./ci/check_sources.sh || fatal` to ci/build_cmake.sh before `mkdir -p build` (script ships in patch 0005, POSIX sh).
User decisions: BLD-13 floor 3.18 (recommended; CI already needs 3.21) vs 3.14 + alt b; BLD-25 host vs target system name (alt b).
