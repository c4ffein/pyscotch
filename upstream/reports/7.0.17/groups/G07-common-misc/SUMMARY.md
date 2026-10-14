# G07-common-misc — summary
| id | status | method | sev | patch |
|----|--------|--------|-----|-------|
| COR-08 | still-present | ran | medium | 0002 (+0003 leak) |
| COR-15 | partially-fixed (debug-only, misses upward wraps) | ran | medium | 0001 |
| COR-18 | fixed-in-7.0.17 | ran | low | - |
| PS-SEP-6 | still-present | ran | low | 0005 |
| COR-17 | partially-fixed (73229e6 adds a local check, hang remains) | ran | medium | 0004 |
| PS-COR-2 | still-present (same defect as COR-17) | ran | medium | 0004 |

5 commits on v7.0.17, `git am`-clean on a fresh clone; 0 warnings in the 32-bit and 64-bit
ASan+UBSan trees; stylecheck/diff --check clean (one pre-existing hit at common_integer.c:604).
extra.json: PS2-G07-1 fork-mode buffer leak (fixed, 0003), PS2-G07-2 GA uses 4/8 bits per
64-bit draw (info, alt diff), PS2-G07-3 gz path leaves the FILE* open after gzclose (info).

Three most important facts:
1. COR-15: 'cmplt 4294967298' still loads as 2 terminals in release 7.0.17 (32-bit), and
   '5000000000' slips past the new debug check; 0001 checks before accumulating (the review's
   formula), unconditionally; 300k-string fuzz 0 mismatches on both int sizes; -O3 graph-load
   cost not measurable (1.08 s patched vs 1.17 s pristine, 72 MB graph). New test_common_integer.
2. COR-17/PS-COR-2: on the 64-bit build, g1/g2/s1/s2 and injected malloc failures hang the
   other ranks; commAllgatherv/commScatterv also silently truncate an unchecked scalar count
   (a1: all ranks return 0 with rank 1's data missing). 0004 checks the scalar on every rank and
   agrees on the error with an int Allreduce before the collective (64-bit Gnum builds only).
3. COR-08: fork mode (no pthreads) hangs with two .gz outputs and prints pending stdout twice
   (reproduced with a 20-line program, which the first pass could not); O_CLOEXEC would not
   help (no exec). 0002 passes the File table to fileCompress/fileDecompress so the child closes
   earlier tasks' pipe ends, and uses _exit(); the check runs a three-child case (hangs on pristine).

Could not do / limits:
- bz2/xz paths not run (no headers on this box); same fork code as gz. check_prog_gcv does not
  exist (gbase/gpart/gord/gmap/gtst run instead). No src/check home for COR-17 (needs > 2^31
  counts or fault injection); the dgraph checks were run on both int sizes. 4-thread outputs
  differ run to run on the same binary, so PS-SEP-6's determinism claim rests on 1-thread runs.

User decisions:
- COR-17: the maintainer guards similar Allreduce agreements with SCOTCH_DEBUG_DGRAPH1 in release
  (dgraph_fold.c:290); 0004 makes it unconditional (data-driven error, slow path only). Alt B keeps
  his debug-only idiom but leaves the release hang.
- COR-15 rejects -INTVALMAX-1 (never a valid file value); alt B accepts it at a division per digit.
