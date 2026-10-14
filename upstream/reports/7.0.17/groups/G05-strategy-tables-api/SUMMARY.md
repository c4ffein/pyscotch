# G05-strategy-tables-api -- summary

Based on G04's parser series (10 commits, patches apply on top with `git am`); my 7 commits in patches/.

- GRA-13   still-present  ran  medium -> patches/0001  (mdeg STRATPARAMINT; + hdgraph & hmesh twins)
- GRA-06   still-present  ran  high   -> patches/0002  (identity ordering in else-less case; + hdgraph & hmesh twins)
- PS-DMO-2 still-present  ran  low    -> G04 patches/0009  (osq default &stratdummy; fixed in base, no G05 patch)
- GRA-15   still-present  ran  low    -> G13 patches/0006  (GRA-02 fully covers it; no G05 patch)
- API-07   still-present  ran  high   -> patches/0003  (reject non-finite/negative + bounded snprintf; 8 builders + 2 tests)
- API-23   still-present  ran  low    -> patches/0005 (coarsen 1->2), 0006 (check Init/stratInit; + dgraphMap twin)
- CLI-01   still-present  ran  high   -> patches/0004  (build default only when no -m; dgmap.c serves dgmap & dgpart)
- PS2-G12-2 still-present ran  medium -> patches/0007  (mapAlloc+kgraphFrst in graphMapCompute2)
- PS2-G13-1 still-present ran  medium -> patches/0007  (mapTerm only on success; same commit)
- PS2-G05-...-1 (extra, medium) distributed dmapSave NULL part array on an incomplete -m strategy (dmapping_io.c:256) -> no patch (dgraph owner)

## Three most important facts
1. GRA-13, GRA-06, API-07, CLI-01 are all genuine and reproduced at runtime; API-07 is a 300+ byte stack
   overflow reachable from a public double argument (balrat=1e300 / DBL_MAX sentinel) -- raised to high.
2. The strategy-table type audit (scripts over every *_st.c) found the mdeg STRATPARAMDOUBLE/Gnum mismatch
   in all three ordering tables (seq graph, dgraph, mesh); the review named only one. Every other table entry
   type-checks against its field. No other STRATPARAMDOUBLE-on-int defect exists.
3. PS-DMO-2 and GRA-15 need no G05 patch: PS-DMO-2 is fixed by G04's &stratdummy-default idiom (patches/0009,
   in this branch's base), GRA-15 by G13's GRA-02 commit (kgraph_map_fm.c). Both verified, referenced, not re-patched.

## Verification
32-bit and 64-bit ASan+UBSan builds, 0 warnings. check_strat_seq (+new cases), check_strat_par (+new cases),
check_scotch_graph_map/map_copy/order/part_ovl/coarsen, check_prog_gmap/gord/mord, check_prog_dgpart all pass.
The bgraph_bipart_ml.c:195 / kgraph_map_ml.c:239 UBSan null-offset notes are pre-existing (untouched files,
identical count pristine vs patched; documented by G13). stylecheck.py and `git diff --check` clean.

## For the user to decide
- API-07 now rejects negative and non-finite ratios (the tools' own `-b` already does); finite 1e30 is accepted by
  the 64-byte-buffer builders and rejected by the 32-byte ones -- no overflow either way. Confirm the rejection policy.
- PS2-G05-...-1 (distributed dmapSave NULL-deref on an incomplete user -m strategy) is in dmapping_io.c /
  the kdgraph path, not a G05 file; route it to the distributed-mapping owner (pre-allocate like graphMapCompute2,
  or reject in dmapSave).
- CLI-01: honouring -m now lets a syntactically-valid-but-incomplete user strategy reach the mapper (above).
