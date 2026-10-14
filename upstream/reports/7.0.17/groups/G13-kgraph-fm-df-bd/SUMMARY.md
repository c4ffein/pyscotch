# G13-kgraph-fm-df-bd -- summary

One line per id (status | method | severity -> patch):
- GRA-02 still-present | ran | high   -> patches/0006 (refresh domnnbr after the fallback; stratExit + error frees)
- GRA-17 still-present | ran | low    -> patches/0007 (publish edge-array size after realloc; 3 callers check)
- GRA-12 still-present | ran | medium -> patches/0005 (route setup failures through the barriers; guard free; +2 debug gotos)
- GRA-18 still-present | ran | low    -> patches/0004 (copy from difotax after the swap)
- GRA-19 still-present | ran | low    -> patches/0002 (DELETE the dead block; review's "make it live" fix is unsafe)
- GRA-20 still-present | ran | low    -> patches/0003 (compare vs saved count; free on OOM path)
- GRA-16 partially-fixed | ran | low  -> patches/0001 (unsigned common.h flag macros + bdgraph_bipart_ex/bd arrays)

Series: 7 commits on v7.0.17, format-patch in patches/, re-applied clean with `git am` on a fresh clone.
Builds 0-warning in both 32-bit and 64-bit Gnum trees; check_scotch_graph_map/order/mesh_graph,
check_prog_gmap/gpart and (PT-Scotch) check_scotch_dgraph_check all pass; no new sanitizer reports
(the bgraph_bipart_ml.c/kgraph_map_ml.c null-offset UBSan hits are pre-existing, identical count
pristine vs patched).

## Three most important facts
1. GRA-02 is a genuine public-API heap-buffer-overflow (SCOTCH_graphMap + an imbalanced frontier-less
   stage, e.g. 'rf{bal=0.00001}'); the fix refreshes the domain count the fallback changed and also
   plugs a leaked fallback strategy and an ignored return code.
2. GRA-19: the review's suggested fix is WRONG. Making the dead isolated-anchor block live trips
   'kgraphCost: invalid load difference' and SEGVs under SCOTCH_DEBUG_ALL, because "anchor has no band
   edge" is not "empty part" once the band strategy repartitions. The safe, behaviour-preserving action
   is to delete the dead code; a correct empty-part freeze needs a maintainer design decision.
3. GRA-16 is only partially fixed upstream: 6a00c51 missed the generic common.h flagSet/flagVal/flagSize
   macros (still signed `int` + `1 <<`), used by the PT-Scotch bipartitioners; completed here.

## Extra finding
PS2-G13-1 (medium): graphMapCompute2 (library_graph_map.c:294-295) calls mapTerm unconditionally after
a failed mapping, dereferencing an unset part array -> SEGV. Exposed once GRA-17 lets FM fail gracefully;
reachable from any mapping-method allocation failure. Fix in alt/ (guard with `if (o == 0)`); not committed
as it is outside this group's files.

## For the user to decide
- GRA-19: accept the deletion (recommended, zero behaviour change) vs. commissioning a correct empty-part
  freeze. The review's/first pass's "make it live" option is in alt/ marked UNSAFE.
- PS2-G13-1 belongs to a library_graph_map.c owner; route it to whoever owns that file.
