# G14-graph-loaders — summary

| id | status | method | sev | patch |
|----|--------|--------|-----|-------|
| GRA-04 | partially-fixed (label half still open) | ran | high | 0001 |
| GRA-10 | partially-fixed (no upper/base bound)   | ran | medium | 0001 |
| GRA-07 | still-present | ran | medium | 0002 |
| GRA-08 | still-present | ran | medium | 0003 |
| GRA-11 | still-present | ran | medium | 0004 |
| GRA-24 | still-present | ran | low | 0005 |
| GRA-09 | still-present | ran | medium | 0006 |
| PS-API-5 | still-present | ran | low | 0007 |

7 commits on v7.0.17, `git am`-clean on a fresh clone; 0 warnings in the 32-bit
and 64-bit ASan+UBSan builds. extra.json: PS2-G14-1 (unbounded header counts /
label values / HB field widths — UBSan/huge-alloc/hang, not committed, design
call), PS2-G14-2 (negative degree + arc-count overflow — fixed inside 0001).

Three most important facts:
1. The four real memory-corruption loaders are closed: a mutation fuzzer over
   .grf/.mtx/.chac/.rsa (2264 mutants, seed 42) dropped from 243 sanitizer hits
   with heap-buffer-overflow/SEGV in graphLoad2, graphGeomLoadChac/Habo/Mmkt
   (before) to 206 hits with ZERO loader memory-corruption (after); residual hits
   are UBSan integer-overflow on absurd inputs (file still rejected) + huge-malloc
   requests that return NULL in production.
2. GRA-04/GRA-10/PS2-G14-2 are one coherent validation of graphLoad's read loop
   (labels, edge ends, degree) rather than scattered guards, per the brief.
3. All required checks pass: check_prog_gbase/gmk/gout/gpart, check_scotch_graph_dump,
   check_prog_gtst, check_scotch_graph_map/order/induce/coarsen, and gcv chac/mtx/hb
   round-trips (ASan) — graphCheck's new label-uniqueness check rejects no valid graph.

Could not do / for the maintainer to decide:
- Twins live in other groups' files and are flagged, not patched: dgraphLoadCent/Dist
  (dgraph_io_load.c, G20) share the unchecked label/edge/degree reads; meshLoad
  (mesh_io.c, G11) shares the label read; meshGeomLoadScot (mesh_io_scot.c, G11) has
  the identical GRA-09 dimension bug; HB mesh checks are SEP-08 (G11).
- PS-API-5: whether graphCheck() may allocate (Option A, committed) or must stay
  allocation-free (Option B, alt). Recommended A: uniqueness is a documented invariant.
- PS2-G14-1: whether to reject non-positive / bound large header counts and HB field
  widths; intLoad() parse overflow is common_integer.c (out of this group).
