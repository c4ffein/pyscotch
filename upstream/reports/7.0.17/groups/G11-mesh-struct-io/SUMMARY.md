# G11-mesh-struct-io — summary (Scotch 7.0.17, series of 11 patches on v7.0.17, applies with `git am`)

SEP-07    fixed-in-7.0.17   ran        high   -> -
PS-SEP-1  still-present     ran        medium -> patches/0001 (MESHVERTGROUP 0x0020; data/small2_lbl.msh)
SEP-23    still-present     ran        low    -> patches/0002 (+0003 hmeshExit alias); test_mesh_base
SEP-21    partially-fixed   ran        low    -> patches/0004 (fake isolated elements; memCpy itself fixed by f36ab36)
SEP-08    still-present     ran        medium -> patches/0007 (unconditional checks, header/width, velosum; data/hb3.pue)
API-08    still-present     ran        medium -> patches/0006 (NULL tag = matrix 0, twin of graphGeomLoadHabo)
SEP-16    still-present     ran        medium -> patches/0008 (+0011); test_scotch_mesh_geom, data/small2*.xyz
API-06    partially-fixed   ran        medium -> patches/0005 (3 mesh I/O wrappers + SCOTCH_meshExit guard)
API-12    partially-fixed   partly-run medium -> patches/0005 (output handles, graphDump; dmesh twin read only)
Extras (extra.json): PS2-…-8 meshLoad hardening (high) -> 0010; PS2-…-3 base change breaks edge ends -> 0009;
PS2-…-5 label semantics -> 0011; PS2-…-2/4/6 -> 0004/0003/0007; PS2-…-1 (meshOrderSave labels), -7 (graph geometry twin),
-9 (Fortran rank string), -10 (stale prototype): alt diffs only.

Three most important facts
1. Every labeled mesh file crashed on exit in 7.0.17 (flag collision, PS-SEP-1) and, independently, meshLoad trusted labels,
   degrees and edge ends: `mord` on a malformed .msh is a heap overflow in hallOrderHd (PS2-8). Both are fixed; the mesh
   loader now has the exact discipline of G14's graphLoad patch (same checks, same messages).
2. The labeled-mesh path was never a round trip: meshLoad added the kind base to labels, meshSave wrote them raw, geometry
   and ordering outputs carried shifted labels. Patch 0011 stores labels verbatim (graphLoad semantics, doc-consistent);
   it is last in the series so it can be dropped alone. Patch 0008 (SEP-16) + 0007/0009/0010 are independent of it.
3. API-06 was only partially fixed upstream: the three mesh geometry I/O wrappers and SCOTCH_meshExit still took raw handles;
   API-12's output handles too. One commit (0005) finishes 6a030db, including the libscotch/Makefile dependency lines.

Verification: 32- and 64-bit ASan/UBSan builds, 0 warnings; check_prog_{mmk,mcv,mord,gmk_msh,gbase}, check_scotch_{mesh_graph,
mesh_geom,graph_dump,context}, check_mesh_base, check_scotch_mesh_build_f (needs ASAN_OPTIONS=detect_leaks=0: the Fortran
test itself leaks on pristine too), check_libparmetis_v3 (MPI) all pass; new tests fail on the pristine library. Fuzz
(repro/fuzz): 12 sanitizer buckets -> 6, all remaining are signed-overflow UB on absurd header values or ordering crashes on
arc-inconsistent meshes (mord/gord do not call Check; meshLoad, like graphLoad, does not verify arc symmetry).

Not done / to decide
- Label semantics (0011) is a format decision: labels must now be unique across elements and nodes.
- PS2-1 (mesh ordering labels), PS2-7 (graph_io_scot.c) and PS2-9 (Fortran rank string, graph wrapper too) touch files of
  other groups: alt diffs only. PS2-10: whether to delete the now-empty mesh_io.h.
- Weighted nodes-first halo meshes in hmeshMesh stay unrepresentable (latent, no caller).
- Stylecheck: only 3 pre-existing hits in untouched lines (library_mesh.c:487, mesh_io_habo.c:147-148).
