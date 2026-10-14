# Fortran API audit of /tmp/claude-1000/-home-dev-workspace-pyscotch/087f3d41-a5d8-4b0a-9260-769d70cf8179/scratchpad/infra/v7.0.17

244 wrappers in *_f.c, 247 C prototypes, 218 C definitions, 231 documented Fortran synopses, 114 findings

ORDER check coverage: declaration-order only: 104, no C definition found: 45, strong: 95

| class | where | what |
|---|---|---|
| CASE | src/libscotch/library_dgraph_stat_f.c:71 | macro names 'DGRAPHSTAT' / 'Dgraphstat' do not agree |
| RETTYPE | src/libscotch/library_arch_f.c:218 | result of SCOTCH_archSize (returns SCOTCH_Num) stored through 'int * const sizeptr' |
| TYPE | src/libscotch/library_arch_dom_f.c:114 | parameter 'wghtptr' is 'SCOTCH_Num * const wghtptr' in the wrapper but 'doubleprecision (*) dom1dat,' in the manual (doc/src/scotch/s_l.tex:2782) |
| TYPE | src/libscotch/library_arch_f.c:218 | parameter 'sizeptr' is 'int * const sizeptr' in the wrapper but 'integer*num archnbr' in the manual (doc/src/scotch/s_l.tex:1895) |
| TYPE | src/libscotch/library_arch_f.c:244 | parameter 'revaptr' is 'int * const revaptr' in the wrapper but 'integer*num (*) velotab,' in the manual (doc/src/scotch/s_l.tex:2113) |
| TYPE | src/libscotch/library_dmesh_build_adm_f.c:71 | parameter 'revaptr' is 'int * const revaptr' in the wrapper but 'integer*num (*) vlblloctab,' in the manual (doc/src/ptscotch/p_l.tex:3896) |
| TYPE | src/libscotch/library_dmesh_dgraph_f.c:68 | parameter 'nocoptr' is 'const SCOTCH_Num * const nocoptr' in the wrapper but 'integer nocoval,' in the manual (doc/src/ptscotch/p_l.tex:4065) |
| TYPE | src/libscotch/library_graph_f.c:243 | parameter 'edloidx' is 'SCOTCH_Idx * const edloidx' in the wrapper but 'integer*num edloidx' in the manual (doc/src/scotch/s_l.tex:3281) |
| TYPE | src/libscotch/library_mesh_f.c:187 | parameter 'revaptr' is 'int * const revaptr' in the wrapper but 'integer*num ierr' in the manual (doc/src/scotch/s_l.tex:5371) |
| TYPE | src/libscotch/library_mesh_f.c:215 | parameter 'revaptr' is 'int * const revaptr' in the wrapper but 'integer*num ierr' in the manual (doc/src/scotch/s_l.tex:5469) |
| TYPE | src/libscotch/library_mesh_graph_f.c:87 | parameter 'nocoptr' is 'const SCOTCH_Num * const nocoptr' in the wrapper but 'integer nocoval,' in the manual (doc/src/scotch/s_l.tex:5755) |
| TYPE | src/libscotch/library_random_f.c:139 | parameter 'procnum' is 'const int * const procnum' in the wrapper but 'integer*num procnum' in the manual (doc/src/scotch/s_l.tex:7632) |
| TYPE | src/libscotch/library_random_f.c:139 | parameter 'procnum' is 'const int * const procnum' in the wrapper but 'integer*num procnum' in the manual (doc/src/ptscotch/p_l.tex:4860) |
| TYPE | src/libscotchmetis/metis_graph_part_f.c:328 | parameter 'tpwgts' is 'const double * const tpwgts' in the wrapper but 'integer*num (*) options,' in the manual (doc/src/scotch/s_l.tex:8711) |
| TYPE | src/libscotchmetis/metis_graph_part_f.c:328 | parameter 'ubvec' is 'const double * const ubvec' in the wrapper but 'integer*num edgecut,' in the manual (doc/src/scotch/s_l.tex:8711) |
| TYPE | src/libscotchmetis/metis_graph_part_f.c:328 | parameter 'tpwgts' is 'const double * const tpwgts' in the wrapper but 'integer*num (*) options,' in the manual (doc/src/scotch/s_l.tex:8765) |
| TYPE | src/libscotchmetis/metis_graph_part_f.c:328 | parameter 'ubvec' is 'const double * const ubvec' in the wrapper but 'integer*num edgecut,' in the manual (doc/src/scotch/s_l.tex:8765) |
| IERR | doc/src/ptscotch/p_l.tex:2340 | manual lists no trailing 'integer ierr' for scotchfdgraphredist (C returns int) |
| IERR | doc/src/scotch/s_l.tex:5371 | manual lists no trailing 'integer ierr' for scotchfmeshbuild (C returns int) |
| IERR | doc/src/scotch/s_l.tex:5469 | manual lists no trailing 'integer ierr' for scotchfmeshbuildelem (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7088 | manual lists no trailing 'integer ierr' for scotchfgraphgeomloadchac (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7129 | manual lists no trailing 'integer ierr' for scotchfgraphgeomloadhabo (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7173 | manual lists no trailing 'integer ierr' for scotchfgraphgeomloadscot (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7216 | manual lists no trailing 'integer ierr' for scotchfgraphgeomsavechac (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7256 | manual lists no trailing 'integer ierr' for scotchfgraphgeomsavescot (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7299 | manual lists no trailing 'integer ierr' for scotchfmeshgeomloadhabo (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7343 | manual lists no trailing 'integer ierr' for scotchfmeshgeomloadscot (C returns int) |
| IERR | doc/src/scotch/s_l.tex:7386 | manual lists no trailing 'integer ierr' for scotchfmeshgeomsavescot (C returns int) |
| IERR | src/libscotch/library_dgraph_map_stat_f.c:68 | C routine SCOTCH_dgraphMapStat returns int but wrapper has no trailing 'int * revaptr' (last: SCOTCH_Num * const cmexsumptr) |
| COUNT | src/libscotch/library_arch_dom_f.c:114 | wrapper has 3 visible parameters, manual (doc/src/scotch/s_l.tex:2782) lists 4 |
| COUNT | src/libscotch/library_arch_f.c:244 | wrapper has 3 visible parameters, manual (doc/src/scotch/s_l.tex:2113) lists 4 |
| COUNT | src/libscotch/library_dgraph_map_stat_f.c:68 | wrapper has 16 visible parameters, manual (doc/src/ptscotch/p_l.tex:3123) lists 17 |
| COUNT | src/libscotch/library_dgraph_redist_f.c:69 | wrapper has 7 visible parameters, manual (doc/src/ptscotch/p_l.tex:2340) lists 6 |
| COUNT | src/libscotch/library_dmesh_build_adm_f.c:71 | wrapper has 8 visible parameters, manual (doc/src/ptscotch/p_l.tex:3896) lists 14 |
| COUNT | src/libscotch/library_graph_io_chac_f.c:128 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7216) lists 5 |
| COUNT | src/libscotch/library_graph_io_chac_f.c:73 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7088) lists 5 |
| COUNT | src/libscotch/library_graph_io_habo_f.c:73 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7129) lists 5 |
| COUNT | src/libscotch/library_graph_io_scot_f.c:128 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7256) lists 5 |
| COUNT | src/libscotch/library_graph_io_scot_f.c:73 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7173) lists 5 |
| COUNT | src/libscotch/library_mesh_io_habo_f.c:73 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7299) lists 5 |
| COUNT | src/libscotch/library_mesh_io_scot_f.c:128 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7386) lists 5 |
| COUNT | src/libscotch/library_mesh_io_scot_f.c:73 | wrapper has 6 visible parameters, manual (doc/src/scotch/s_l.tex:7343) lists 5 |
| COUNT | src/libscotchmetis/metis_graph_part_f.c:328 | wrapper has 13 visible parameters, manual (doc/src/scotch/s_l.tex:8711) lists 11 |
| COUNT | src/libscotchmetis/metis_graph_part_f.c:328 | wrapper has 13 visible parameters, manual (doc/src/scotch/s_l.tex:8765) lists 11 |
| NOWRAP | doc/src/ptscotch/p_l.tex:2075 | manual documents 'scotchfdgraphfree' (section SCOTCH_dgraphFree) but no *_f.c defines it |
| NOWRAP | doc/src/ptscotch/p_l.tex:2142 | manual documents 'scotchfdgraphgrow' (section SCOTCH_dgraphGrow) but no *_f.c defines it |
| NOWRAP | doc/src/ptscotch/p_l.tex:3423 | manual documents 'scotchfgraphdorderexit' (section SCOTCH_dgraphOrderExit) but no *_f.c defines it |
| NOWRAP | doc/src/ptscotch/p_l.tex:3528 | manual documents 'scotchfgraphdordersavemap' (section SCOTCH_dgraphOrderSaveMap) but no *_f.c defines it |
| NOWRAP | doc/src/ptscotch/p_l.tex:4128 | manual documents 'scotchfdmeshfree' (section SCOTCH_dmeshFree) but no *_f.c defines it |
| NOWRAP | doc/src/ptscotch/p_l.tex:4678 | manual documents 'scotchfdmapsizeof' (section SCOTCH_dmapSizeof) but no *_f.c defines it |
| NOWRAP | doc/src/ptscotch/p_l.tex:4721 | manual documents 'scotchfdordersizeof' (section SCOTCH_dorderSizeof) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:1959 | manual documents 'scotchfarchbuild0' (section SCOTCH_archBuild0) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:2032 | manual documents 'scotchfarchbuild2' (section SCOTCH_archBuild2) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:2178 | manual documents 'scotchfarchltleaf' (section SCOTCH_archLtleaf) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:5182 | manual documents 'scotchfgraphorderload' (section SCOTCH_graphOrderLoad) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:5967 | manual documents 'scotchfmeshstat' (section SCOTCH_meshStat) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:6486 | manual documents 'scotchfstratsizeof' (section SCOTCH_stratSizeof) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:7450 | manual documents 'scotchfmapsizeof' (section SCOTCH_mapSizeof) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:7493 | manual documents 'scotchfordersizeof' (section SCOTCH_orderSizeof) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:8660 | manual documents 'metis_nodwend' (section METIS_NodeWND) but no *_f.c defines it |
| NOWRAP | doc/src/scotch/s_l.tex:8890 | manual documents 'metis_metistodual' (section METIS_PartMeshDual) but no *_f.c defines it |
| NODOC | src/libscotch/library_arch_dom_f.c:128 | wrapper 'archdomdist' has no Fortran synopsis in the manuals (C routine SCOTCH_archDomDist has a section) |
| NODOC | src/libscotch/library_arch_f.c:231 | wrapper 'archvar' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_arch_f.c:258 | wrapper 'archcmpltw' has no Fortran synopsis in the manuals (C routine SCOTCH_archCmpltw has a section) |
| NODOC | src/libscotch/library_arch_f.c:273 | wrapper 'archcmpltws' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_arch_f.c:333 | wrapper 'archmeshx' has no Fortran synopsis in the manuals (C routine SCOTCH_archMeshX has a section) |
| NODOC | src/libscotch/library_arch_f.c:411 | wrapper 'archtorusx' has no Fortran synopsis in the manuals (C routine SCOTCH_archTorusX has a section) |
| NODOC | src/libscotch/library_dgraph_halo_f.c:137 | wrapper 'dgraphhaloreqsizeof' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_dgraph_order_f.c:87 | wrapper 'dgraphorderexit' has no Fortran synopsis in the manuals (C routine SCOTCH_dgraphOrderExit has a section) |
| NODOC | src/libscotch/library_dgraph_order_io_block_f.c:69 | wrapper 'dgraphordersaveblock' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_dgraph_order_io_f.c:67 | wrapper 'dgraphordersavemap' has no Fortran synopsis in the manuals (C routine SCOTCH_dgraphOrderSaveMap has a section) |
| NODOC | src/libscotch/library_graph_io_mmkt_f.c:128 | wrapper 'graphgeomsavemmkt' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_graph_io_mmkt_f.c:73 | wrapper 'graphgeomloadmmkt' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_graph_order_f.c:269 | wrapper 'graphorderlist' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_mesh_order_f.c:231 | wrapper 'meshordercomputelist' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_mesh_order_f.c:268 | wrapper 'meshorderlist' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_parser_f.c:95 | wrapper 'stratfree' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_random_f.c:105 | wrapper 'randomsave' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotch/library_random_f.c:151 | wrapper 'randomreset' has no Fortran synopsis in the manuals (C routine SCOTCH_randomReset has a section) |
| NODOC | src/libscotch/library_random_f.c:71 | wrapper 'randomload' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotchmetis/metis_graph_order_f.c:233 | wrapper 'metis_nodewnd' has no Fortran synopsis in the manuals (C routine not documented either) |
| NODOC | src/libscotchmetis/metis_graph_part_dual_f.c:111 | wrapper 'metis_partmeshdual' has no Fortran synopsis in the manuals (C routine not documented either) |
| DOCNAME | doc/src/ptscotch/p_l.tex:3423 | Fortran synopsis is named 'scotchfgraphdorderexit' in section SCOTCH_dgraphOrderExit (expected 'scotchfdgraphorderexit') |
| DOCNAME | doc/src/ptscotch/p_l.tex:3528 | Fortran synopsis is named 'scotchfgraphdordersavemap' in section SCOTCH_dgraphOrderSaveMap (expected 'scotchfdgraphordersavemap') |
| DOCNAME | doc/src/scotch/s_l.tex:2113 | Fortran synopsis is named 'scotchfarchcmplt' in section SCOTCH_archCmpltw (expected 'scotchfarchcmpltw') |
| DOCNAME | doc/src/scotch/s_l.tex:2782 | Fortran synopsis is named 'scotchfarchdomwght' in section SCOTCH_archDomDist (expected 'scotchfarchdomdist') |
| DOCORDER | doc/src/ptscotch/p_l.tex:3123 | Fortran synopsis order (grafdat,, mappdat,, tgtnbr,, mapnbr,, mapmax,, mapmin,, mapavg,, mapdlt,, ngbsum,, ngbmin,, ngbmax,, cdstmax,, cdsttab,, cmlosum,, cmdisum,, cmexsum,) differs from C synopsis order (grafptr,, mappptr,, tgtnbrptr,, mapnbrptr,, mapminptr,, mapmaxptr,, mapavgptr,, mapdltptr,, ngbsumptr,, ngbminptr,, ngbmaxptr,, cdstmaxptr,, cdsttab[256],, cmlosumptr,, cmdisumptr,, cmexsumptr) |
| DOCC | doc/src/ptscotch/p_l.tex:3104 | C synopsis of SCOTCH_dgraphMapStat arg 13 'SCOTCH_Num cdsttab[256],' vs library.h 'SCOTCH_Num [256]' |
| DOCC | doc/src/ptscotch/p_l.tex:3880 | C synopsis of SCOTCH_dmeshBuildAdm has 13 args, library.h has 7 |
| DOCC | doc/src/ptscotch/p_l.tex:4764 | C synopsis of SCOTCH_errorPrint has 1 args, library.h has 2 |
| DOCC | doc/src/ptscotch/p_l.tex:4779 | C synopsis of SCOTCH_errorPrintW has 1 args, library.h has 2 |
| DOCC | doc/src/scotch/s_l.tex:1825 | C synopsis of SCOTCH_archName returns 'const char *', library.h says 'char *' |
| DOCC | doc/src/scotch/s_l.tex:2107 | C synopsis of SCOTCH_archCmpltw arg 3 'const SCOTCH_Num velotab' vs library.h 'const SCOTCH_Num * const' |
| DOCC | doc/src/scotch/s_l.tex:2169 | C synopsis names SCOTCH_archLtleaf, which is not in library.h / library_pt.h |
| DOCC | doc/src/scotch/s_l.tex:2872 | C synopsis of SCOTCH_graphBase returns 'int', library.h says 'SCOTCH_Num' |
| DOCC | doc/src/scotch/s_l.tex:7536 | C synopsis of SCOTCH_errorPrint has 1 args, library.h has 2 |
| DOCC | doc/src/scotch/s_l.tex:7551 | C synopsis of SCOTCH_errorPrintW has 1 args, library.h has 2 |
| DOCC | doc/src/scotch/s_l.tex:8464 | C synopsis of SCOTCH_version returns 'int', library.h says 'void' |
| DOCTYPE | doc/src/ptscotch/p_l.tex:5154 | malformed Fortran type 'integer*num (**)' for argument 'xadj,' |
| DOCTYPE | doc/src/ptscotch/p_l.tex:5154 | malformed Fortran type 'integer*num (**)' for argument 'adjncy,' |
| DOCTYPE | doc/src/ptscotch/p_l.tex:5253 | malformed Fortran type 'float (*)' for argument 'xyz,' |
| DOCTYPE | doc/src/ptscotch/p_l.tex:5253 | malformed Fortran type 'float (*)' for argument 'tpwgts,' |
| DOCTYPE | doc/src/ptscotch/p_l.tex:5253 | malformed Fortran type 'float (*)' for argument 'ubvec,' |
| DOCTYPE | doc/src/ptscotch/p_l.tex:5311 | malformed Fortran type 'float (*)' for argument 'tpwgts,' |
| DOCTYPE | doc/src/ptscotch/p_l.tex:5311 | malformed Fortran type 'float (*)' for argument 'ubvec,' |
| DOCTYPE | doc/src/scotch/s_l.tex:3228 | malformed Fortran type 'integernum' for argument 'colonbr,' |
| DOCTYPE | doc/src/scotch/s_l.tex:3228 | malformed Fortran type 'integernum' for argument 'flagval,' |
| DOCTYPE | doc/src/scotch/s_l.tex:3361 | malformed Fortran type 'integernum' for argument 'diamval' |
| DOCTYPE | doc/src/scotch/s_l.tex:3479 | malformed Fortran type 'integernum (*)' for argument 'vnumtab,' |
| DOCTYPE | doc/src/scotch/s_l.tex:3515 | malformed Fortran type 'characternum (*)' for argument 'parttab,' |
| DOCTYPE | doc/src/scotch/s_l.tex:3515 | malformed Fortran type 'characternum' for argument 'partval,' |
| DOCTYPE | doc/src/scotch/s_l.tex:8566 | malformed Fortran type 'integer*num (**)' for argument 'xadj,' |
| DOCTYPE | doc/src/scotch/s_l.tex:8566 | malformed Fortran type 'integer*num (**)' for argument 'adjncy' |
| DOCTYPE | doc/src/scotch/s_l.tex:8890 | malformed Fortran type 'doubleprecision* (*)' for argument 'tpwgts,' |

## C routines with no Fortran wrapper at all (informational)

- SCOTCH_archAlloc (src/libscotch/library.h)
- SCOTCH_archBuild0 (src/libscotch/library.h)
- SCOTCH_archBuild2 (src/libscotch/library.h)
- SCOTCH_archDomAlloc (src/libscotch/library.h)
- SCOTCH_contextAlloc (src/libscotch/library.h)
- SCOTCH_contextOptionParse (src/libscotch/library.h)
- SCOTCH_dgraphAlloc (src/libscotch/library_pt.h)
- SCOTCH_dgraphFree (src/libscotch/library_pt.h)
- SCOTCH_dgraphGrow (src/libscotch/library_pt.h)
- SCOTCH_dgraphHaloReqAlloc (src/libscotch/library_pt.h)
- SCOTCH_dmapAlloc (src/libscotch/library_pt.h)
- SCOTCH_dmapSizeof (src/libscotch/library_pt.h)
- SCOTCH_dmeshAlloc (src/libscotch/library_pt.h)
- SCOTCH_dmeshFree (src/libscotch/library_pt.h)
- SCOTCH_dorderAlloc (src/libscotch/library_pt.h)
- SCOTCH_dorderSizeof (src/libscotch/library_pt.h)
- SCOTCH_errorPrint (src/libscotch/library.h)
- SCOTCH_errorPrintW (src/libscotch/library.h)
- SCOTCH_errorProg (src/libscotch/library.h)
- SCOTCH_geomAlloc (src/libscotch/library.h)
- SCOTCH_graphAlloc (src/libscotch/library.h)
- SCOTCH_graphDump (src/libscotch/library.h)
- SCOTCH_graphOrderLoad (src/libscotch/library.h)
- SCOTCH_graphPartOvlView (src/libscotch/library.h)
- SCOTCH_graphRemapView (src/libscotch/library.h)
- SCOTCH_graphRemapViewRaw (src/libscotch/library.h)
- SCOTCH_mapAlloc (src/libscotch/library.h)
- SCOTCH_mapSizeof (src/libscotch/library.h)
- SCOTCH_memFree (src/libscotch/library.h)
- SCOTCH_meshAlloc (src/libscotch/library.h)
- SCOTCH_meshStat (src/libscotch/library.h)
- SCOTCH_orderAlloc (src/libscotch/library.h)
- SCOTCH_orderSizeof (src/libscotch/library.h)
- SCOTCH_stratAlloc (src/libscotch/library.h)
- SCOTCH_stratSizeof (src/libscotch/library.h)

## Wrapper inventory

| wrapper | file:line | C target | params |
|---|---|---|---|
| stratgraphbipart | src/libscotch/library_arch_build_f.c:72 | SCOTCH_stratGraphBipart | SCOTCH_Strat * const straptr; const char * const string; int * const revaptr; const int strnbr |
| archbuild | src/libscotch/library_arch_build_f.c:99 | SCOTCH_archBuild | SCOTCH_Arch * const archptr; SCOTCH_Graph * const grafptr; const SCOTCH_Num * const listnbr; const SCOTCH_Num * const listptr; SCOTCH_Strat * const straptr; int * const revaptr |
| archdomnum | src/libscotch/library_arch_dom_f.c:71 | SCOTCH_archDomNum | SCOTCH_Arch * const archptr; SCOTCH_ArchDom * const domnptr; SCOTCH_Num * const dnumptr |
| archdomterm | src/libscotch/library_arch_dom_f.c:85 | SCOTCH_archDomTerm | SCOTCH_Arch * const archptr; SCOTCH_ArchDom * const domnptr; const SCOTCH_Num * const dnumptr; int * const revaptr |
| archdomsize | src/libscotch/library_arch_dom_f.c:100 | SCOTCH_archDomSize | SCOTCH_Arch * const archptr; const SCOTCH_ArchDom * const domnptr; SCOTCH_Num * const sizeptr |
| archdomwght | src/libscotch/library_arch_dom_f.c:114 | SCOTCH_archDomWght | SCOTCH_Arch * const archptr; const SCOTCH_ArchDom * const domnptr; SCOTCH_Num * const wghtptr |
| archdomdist | src/libscotch/library_arch_dom_f.c:128 | SCOTCH_archDomDist | SCOTCH_Arch * const archptr; const SCOTCH_ArchDom * const dom0ptr; const SCOTCH_ArchDom * const dom1ptr; SCOTCH_Num * const distptr |
| archdomfrst | src/libscotch/library_arch_dom_f.c:143 | SCOTCH_archDomFrst | SCOTCH_Arch * const archptr; SCOTCH_ArchDom * const domnptr; int * const revaptr |
| archdombipart | src/libscotch/library_arch_dom_f.c:157 | SCOTCH_archDomBipart | SCOTCH_Arch * const archptr; const SCOTCH_ArchDom * const domnptr; SCOTCH_ArchDom * const dom0ptr; SCOTCH_ArchDom * const dom1ptr; int * const revaptr |
| archinit | src/libscotch/library_arch_f.c:78 | SCOTCH_archInit | SCOTCH_Arch * const archptr; int * const revaptr |
| archexit | src/libscotch/library_arch_f.c:91 | SCOTCH_archExit | SCOTCH_Arch * const archptr |
| archsizeof | src/libscotch/library_arch_f.c:103 | SCOTCH_archSizeof | int * const sizeptr |
| archdomsizeof | src/libscotch/library_arch_f.c:115 | SCOTCH_archDomSizeof | int * const sizeptr |
| archload | src/libscotch/library_arch_f.c:131 | SCOTCH_archLoad | SCOTCH_Arch * const archptr; int * const fileptr; int * const revaptr |
| archsave | src/libscotch/library_arch_f.c:166 | SCOTCH_archSave | SCOTCH_Arch * const archptr; int * const fileptr; int * const revaptr |
| archname | src/libscotch/library_arch_f.c:201 | SCOTCH_archName | SCOTCH_Arch * const archptr; char * const chartab; int * const charptr |
| archsize | src/libscotch/library_arch_f.c:218 | SCOTCH_archSize | SCOTCH_Arch * const archptr; int * const sizeptr |
| archvar | src/libscotch/library_arch_f.c:231 | SCOTCH_archVar | SCOTCH_Arch * const archptr; int * const flagptr |
| archcmplt | src/libscotch/library_arch_f.c:244 | SCOTCH_archCmplt | SCOTCH_Arch * const archptr; const SCOTCH_Num * const vertnbr; int * const revaptr |
| archcmpltw | src/libscotch/library_arch_f.c:258 | SCOTCH_archCmpltw | SCOTCH_Arch * const archptr; const SCOTCH_Num * const vertnbr; const SCOTCH_Num * const velotab; int * const revaptr |
| archcmpltws | src/libscotch/library_arch_f.c:273 | SCOTCH_archCmpltws | SCOTCH_Arch * const archptr; const SCOTCH_Num * const vertnbr; const SCOTCH_Num * const velotab; int * const revaptr |
| archhcub | src/libscotch/library_arch_f.c:288 | SCOTCH_archHcub | SCOTCH_Arch * const archptr; const SCOTCH_Num * const dimnmax; int * const revaptr |
| archmesh2 | src/libscotch/library_arch_f.c:302 | SCOTCH_archMesh2 | SCOTCH_Arch * const archptr; const SCOTCH_Num * const dimxval; const SCOTCH_Num * const dimyval; int * const revaptr |
| archmesh3 | src/libscotch/library_arch_f.c:317 | SCOTCH_archMesh3 | SCOTCH_Arch * const archptr; const SCOTCH_Num * const dimxval; const SCOTCH_Num * const dimyval; const SCOTCH_Num * const dimzval; int * const revaptr |
| archmeshx | src/libscotch/library_arch_f.c:333 | SCOTCH_archMeshX | SCOTCH_Arch * const archptr; const SCOTCH_Num * const dimnnbr; const SCOTCH_Num * const dimntab; int * const revaptr |
| archsub | src/libscotch/library_arch_f.c:348 | SCOTCH_archSub | SCOTCH_Arch * const subarchptr; SCOTCH_Arch * const orgarchptr; const SCOTCH_Num * const vnumnbr; const SCOTCH_Num * const vnumtab; int * const revaptr |
| archtleaf | src/libscotch/library_arch_f.c:364 | SCOTCH_archTleaf | SCOTCH_Arch * const archptr; const SCOTCH_Num * const levlnbr; const SCOTCH_Num * const sizetab; const SCOTCH_Num * const linktab; int * const revaptr |
| archtorus2 | src/libscotch/library_arch_f.c:380 | SCOTCH_archTorus2 | SCOTCH_Arch * const archptr; const SCOTCH_Num * const dimxval; const SCOTCH_Num * const dimyval; int * const revaptr |
| archtorus3 | src/libscotch/library_arch_f.c:395 | SCOTCH_archTorus3 | SCOTCH_Arch * const archptr; const SCOTCH_Num * const dimxval; const SCOTCH_Num * const dimyval; const SCOTCH_Num * const dimzval; int * const revaptr |
| archtorusx | src/libscotch/library_arch_f.c:411 | SCOTCH_archTorusX | SCOTCH_Arch * const archptr; const SCOTCH_Num * const dimnnbr; const SCOTCH_Num * const dimntab; int * const revaptr |
| archvcmplt | src/libscotch/library_arch_f.c:426 | SCOTCH_archVcmplt | SCOTCH_Arch * const archptr; int * const revaptr |
| archvhcub | src/libscotch/library_arch_f.c:439 | SCOTCH_archVhcub | SCOTCH_Arch * const archptr; int * const revaptr |
| memcur | src/libscotch/library_common_f.c:70 | SCOTCH_memCur | SCOTCH_Idx * const memoptr |
| memmax | src/libscotch/library_common_f.c:82 | SCOTCH_memMax | SCOTCH_Idx * const memoptr |
| contextbinddgraph | src/libscotch/library_context_dgraph_f.c:67 | SCOTCH_contextBindDgraph | SCOTCH_Context * const contptr; const SCOTCH_Dgraph * const orggrafptr; SCOTCH_Dgraph * const cntgrafptr; int * const revaptr |
| contextinit | src/libscotch/library_context_f.c:67 | SCOTCH_contextInit | SCOTCH_Context * const contptr; int * const revaptr |
| contextexit | src/libscotch/library_context_f.c:80 | SCOTCH_contextExit | SCOTCH_Context * const contptr |
| contextsizeof | src/libscotch/library_context_f.c:92 | SCOTCH_contextSizeof | int * const sizeptr |
| contextrandomclone | src/libscotch/library_context_f.c:104 | SCOTCH_contextRandomClone | SCOTCH_Context * const contptr; int * const revaptr |
| contextrandomreset | src/libscotch/library_context_f.c:117 | SCOTCH_contextRandomReset | SCOTCH_Context * const contptr |
| contextrandomseed | src/libscotch/library_context_f.c:129 | SCOTCH_contextRandomSeed | SCOTCH_Context * const contptr; SCOTCH_Num * const seedptr |
| contextthreadimport1 | src/libscotch/library_context_f.c:142 | SCOTCH_contextThreadImport1 | SCOTCH_Context * const contptr; int * const thrdptr; int * const revaptr |
| contextthreadimport2 | src/libscotch/library_context_f.c:156 | SCOTCH_contextThreadImport2 | SCOTCH_Context * const contptr; int * const thrdptr; int * const revaptr |
| contextthreadspawn | src/libscotch/library_context_f.c:170 | SCOTCH_contextThreadSpawn | SCOTCH_Context * const contptr; int * const thrdptr; const int * const coreptr; int * const revaptr |
| contextoptiongetnum | src/libscotch/library_context_f.c:185 | SCOTCH_contextOptionGetNum | SCOTCH_Context * const contptr; const int * const optinumptr; SCOTCH_Num * const optivalptr; int * const revaptr |
| contextoptionsetnum | src/libscotch/library_context_f.c:200 | SCOTCH_contextOptionSetNum | SCOTCH_Context * const contptr; const int * const optinumptr; SCOTCH_Num * const optivalptr; int * const revaptr |
| contextbindgraph | src/libscotch/library_context_graph_f.c:67 | SCOTCH_contextBindGraph | SCOTCH_Context * const contptr; const SCOTCH_Graph * const orggrafptr; SCOTCH_Graph * const cntgrafptr; int * const revaptr |
| contextbindmesh | src/libscotch/library_context_mesh_f.c:67 | SCOTCH_contextBindMesh | SCOTCH_Context * const contptr; const SCOTCH_Mesh * const orgmeshptr; SCOTCH_Mesh * const cntmeshptr; int * const revaptr |
| dgraphband | src/libscotch/library_dgraph_band_f.c:70 | SCOTCH_dgraphBand | SCOTCH_Dgraph * const srcgrafptr; const SCOTCH_Num * fronlocnbr; SCOTCH_Num * const fronloctab; const SCOTCH_Num * distval; SCOTCH_Dgraph * const bndgrafptr; int * const revaptr |
| dgraphbuild | src/libscotch/library_dgraph_build_f.c:71 | SCOTCH_dgraphBuild | SCOTCH_Dgraph * const grafptr; const SCOTCH_Num * const baseval; const SCOTCH_Num * const vertlocnbr; const SCOTCH_Num * const vertlocmax; SCOTCH_Num * const vertloctab; SCOTCH_Num * const vendloctab; SCOTCH_Num * const veloloctab; SCOTCH_Num * const vlblloctab; const SCOTCH_Num * const edgelocnbr; const SCOTCH_Num * const edgelocsiz; SCOTCH_Num * const edgeloctab; SCOTCH_Num * const edgegsttab; SCOTCH_Num * const edloloctab; int * const revaptr |
| dgraphbuildgrid3d | src/libscotch/library_dgraph_build_grid3d_f.c:74 | SCOTCH_dgraphBuildGrid3D | SCOTCH_Dgraph * const grafptr; const SCOTCH_Num * const baseval; const SCOTCH_Num * const dimxval; const SCOTCH_Num * const dimyval; const SCOTCH_Num * const dimzval; const SCOTCH_Num * const incrval; const SCOTCH_Num * const flagval; int * const revaptr |
| dgraphcheck | src/libscotch/library_dgraph_check_f.c:72 | SCOTCH_dgraphCheck | const SCOTCH_Dgraph * const grafptr; int * const revaptr |
| dgraphcoarsenvertlocmax | src/libscotch/library_dgraph_coarsen_f.c:71 | SCOTCH_dgraphCoarsenVertLocMax | SCOTCH_Dgraph * const finegrafptr; const SCOTCH_Num * const flagval; SCOTCH_Num * const coarvertlocmax |
| dgraphcoarsen | src/libscotch/library_dgraph_coarsen_f.c:85 | SCOTCH_dgraphCoarsen | SCOTCH_Dgraph * const finegrafptr; const SCOTCH_Num * const coarnbrptr; double * const coarrat; const SCOTCH_Num * const flagval; SCOTCH_Dgraph * const coargrafptr; SCOTCH_Num * const multloctab; int * const revaptr |
| dgraphinit | src/libscotch/library_dgraph_f.c:75 | SCOTCH_dgraphInit | SCOTCH_Dgraph * const grafptr; const MPI_Fint * const commptr; int * const revaptr |
| dgraphexit | src/libscotch/library_dgraph_f.c:92 | SCOTCH_dgraphExit | SCOTCH_Dgraph * const grafptr |
| dgraphsizeof | src/libscotch/library_dgraph_f.c:104 | SCOTCH_dgraphSizeof | int * const sizeptr |
| dgraphsize | src/libscotch/library_dgraph_f.c:116 | SCOTCH_dgraphSize | const SCOTCH_Dgraph * const grafptr; SCOTCH_Num * const vertglbptr; SCOTCH_Num * const vertlocptr; SCOTCH_Num * const edgeglbptr; SCOTCH_Num * const edgelocptr |
| dgraphdata | src/libscotch/library_dgraph_f.c:132 | SCOTCH_dgraphData | const SCOTCH_Dgraph * const grafptr; const SCOTCH_Num * const indxptr; SCOTCH_Num * const baseptr; SCOTCH_Num * const vertglbptr; SCOTCH_Num * const vertlocptr; SCOTCH_Num * const vertlocptz; SCOTCH_Num * const vertgstptr; SCOTCH_Idx * const vertlocidx; SCOTCH_Idx * const vendlocidx; SCOTCH_Idx * const velolocidx; SCOTCH_Idx * const vlbllocidx; SCOTCH_Num * const edgeglbptr; SCOTCH_Num * const edgelocptr; SCOTCH_Num * const edgelocptz; SCOTCH_Idx * const edgelocidx; SCOTCH_Idx * const edgegstidx; SCOTCH_Idx * const edlolocidx; MPI_Fint * const commptr |
| dgraphgather | src/libscotch/library_dgraph_gather_f.c:72 | SCOTCH_dgraphGather | SCOTCH_Dgraph * const dgrfptr; SCOTCH_Graph * const cgrfptr; int * const revaptr |
| dgraphghst | src/libscotch/library_dgraph_halo_f.c:74 | SCOTCH_dgraphGhst | SCOTCH_Dgraph * const grafptr; int * const revaptr |
| dgraphhalo | src/libscotch/library_dgraph_halo_f.c:87 | SCOTCH_dgraphHalo | SCOTCH_Dgraph * const grafptr; void * const datatab; MPI_Fint * const typeptr; int * const revaptr |
| dgraphhaloasync | src/libscotch/library_dgraph_halo_f.c:105 | SCOTCH_dgraphHaloAsync | SCOTCH_Dgraph * const grafptr; void * const datatab; MPI_Fint * const typeptr; SCOTCH_DgraphHaloReq * const requptr; int * const revaptr |
| dgraphhalowait | src/libscotch/library_dgraph_halo_f.c:124 | SCOTCH_dgraphHaloWait | SCOTCH_DgraphHaloReq * const requptr; int * const revaptr |
| dgraphhaloreqsizeof | src/libscotch/library_dgraph_halo_f.c:137 | SCOTCH_dgraphHaloReqSizeof | int * const sizeptr |
| dgraphinducepart | src/libscotch/library_dgraph_induce_f.c:70 | SCOTCH_dgraphInducePart | SCOTCH_Dgraph * const orggrafptr; SCOTCH_Num * const orgpartloctab; SCOTCH_Num * const indpartval; SCOTCH_Num * const indvertlocnbr; SCOTCH_Dgraph * const indgrafptr; int * const revaptr |
| dgraphload | src/libscotch/library_dgraph_io_load_f.c:77 | SCOTCH_dgraphLoad | SCOTCH_Dgraph * const grafptr; int * const fileptr; const SCOTCH_Num * const baseval; const SCOTCH_Num * const flagval; int * const revaptr |
| dgraphsave | src/libscotch/library_dgraph_io_save_f.c:73 | SCOTCH_dgraphSave | SCOTCH_Dgraph * const grafptr; int * const fileptr; int * const revaptr |
| dgraphmapinit | src/libscotch/library_dgraph_map_f.c:71 | SCOTCH_dgraphMapInit | const SCOTCH_Dgraph * const grafptr; SCOTCH_Dmapping * const mappptr; const SCOTCH_Arch * const archptr; SCOTCH_Num * const termloctab; int * const revaptr |
| dgraphmapexit | src/libscotch/library_dgraph_map_f.c:87 | SCOTCH_dgraphMapExit | const SCOTCH_Dgraph * const grafptr; SCOTCH_Dmapping * const mappptr |
| dgraphmapsave | src/libscotch/library_dgraph_map_f.c:100 | SCOTCH_dgraphMapSave | const SCOTCH_Dgraph * const grafptr; SCOTCH_Dmapping * const mappptr; int * const fileptr; int * const revaptr |
| dgraphmapcompute | src/libscotch/library_dgraph_map_f.c:136 | SCOTCH_dgraphMapCompute | SCOTCH_Dgraph * const grafptr; SCOTCH_Dmapping * const mappptr; SCOTCH_Strat * const straptr; int * const revaptr |
| dgraphmap | src/libscotch/library_dgraph_map_f.c:151 | SCOTCH_dgraphMap | SCOTCH_Dgraph * const grafptr; const SCOTCH_Arch * const archptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const partloctab; int * const revaptr |
| dgraphpart | src/libscotch/library_dgraph_map_f.c:167 | SCOTCH_dgraphPart | SCOTCH_Dgraph * const grafptr; const SCOTCH_Num * const partnbr; SCOTCH_Strat * const straptr; SCOTCH_Num * const partloctab; int * const revaptr |
| stratdgraphmap | src/libscotch/library_dgraph_map_f.c:183 | SCOTCH_stratDgraphMap | SCOTCH_Strat * const straptr; const char * const string; int * const revaptr; const int strnbr |
| stratdgraphmapbuild | src/libscotch/library_dgraph_map_f.c:210 | SCOTCH_stratDgraphMapBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const SCOTCH_Num * const procnbr; const SCOTCH_Num * const partnbr; const double * const kbalval; int * const revaptr |
| stratdgraphclusterbuild | src/libscotch/library_dgraph_map_f.c:227 | SCOTCH_stratDgraphClusterBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const SCOTCH_Num * const procnbr; const SCOTCH_Num * const pwgtval; const double * const densval; const double * const bbalval; int * const revaptr |
| dgraphmapstat | src/libscotch/library_dgraph_map_stat_f.c:68 | SCOTCH_dgraphMapStat | SCOTCH_Dgraph * const grafptr; const SCOTCH_Dmapping * const mapptr; SCOTCH_Num * const tgtnbrptr; SCOTCH_Num * const mapnbrptr; SCOTCH_Num * const mapminptr; SCOTCH_Num * const mapmaxptr; double * const mapavgptr; double * const mapdltptr; SCOTCH_Num * const ngbsumptr; SCOTCH_Num * const ngbminptr; SCOTCH_Num * const ngbmaxptr; SCOTCH_Num * const cdstmaxptr; SCOTCH_Num cdsttab[256]; SCOTCH_Num * const cmlosumptr; SCOTCH_Num * const cmdisumptr; SCOTCH_Num * const cmexsumptr |
| dgraphmapview | src/libscotch/library_dgraph_map_view_f.c:71 | SCOTCH_dgraphMapView | SCOTCH_Dgraph * const grafptr; const SCOTCH_Dmapping * const mapptr; int * const fileptr; int * const revaptr |
| dgraphorderinit | src/libscotch/library_dgraph_order_f.c:73 | SCOTCH_dgraphOrderInit | const SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const ordeptr; int * const revaptr |
| dgraphorderexit | src/libscotch/library_dgraph_order_f.c:87 | SCOTCH_dgraphOrderExit | const SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const ordeptr |
| dgraphordersave | src/libscotch/library_dgraph_order_f.c:100 | SCOTCH_dgraphOrderSave | const SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const ordeptr; int * const fileptr; int * const revaptr |
| dgraphordercompute | src/libscotch/library_dgraph_order_f.c:140 | SCOTCH_dgraphOrderCompute | SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const ordeptr; SCOTCH_Strat * const straptr; int * const revaptr |
| dgraphordercomputelist | src/libscotch/library_dgraph_order_f.c:155 | SCOTCH_dgraphOrderComputeList | SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const ordeptr; const SCOTCH_Num * listptr; const SCOTCH_Num * const listtab; SCOTCH_Strat * const straptr; int * const revaptr |
| stratdgraphorder | src/libscotch/library_dgraph_order_f.c:172 | SCOTCH_stratDgraphOrder | SCOTCH_Strat * const straptr; const char * const string; int * const revaptr; const int strnbr |
| stratdgraphorderbuild | src/libscotch/library_dgraph_order_f.c:199 | SCOTCH_stratDgraphOrderBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const SCOTCH_Num * const procnbr; const SCOTCH_Num * const levlnbr; const double * const bbalval; int * const revaptr |
| dgraphcorderinit | src/libscotch/library_dgraph_order_gather_f.c:67 | SCOTCH_dgraphCorderInit | const SCOTCH_Dgraph * const grafptr; SCOTCH_Ordering * const ordeptr; SCOTCH_Num * const permtab; SCOTCH_Num * const peritab; SCOTCH_Num * const cblkptr; SCOTCH_Num * const rangtab; SCOTCH_Num * const treetab; int * const revaptr |
| dgraphcorderexit | src/libscotch/library_dgraph_order_gather_f.c:87 | SCOTCH_dgraphCorderExit | const SCOTCH_Dgraph * const grafptr; SCOTCH_Ordering * const ordeptr |
| dgraphordergather | src/libscotch/library_dgraph_order_gather_f.c:100 | SCOTCH_dgraphOrderGather | const SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const dordptr; SCOTCH_Ordering * const cordptr; int * const revaptr |
| dgraphordersaveblock | src/libscotch/library_dgraph_order_io_block_f.c:69 | SCOTCH_dgraphOrderSaveBlock | const SCOTCH_Dgraph * const grafptr; const SCOTCH_Dordering * const ordeptr; int * const fileptr; int * const revaptr |
| dgraphordersavemap | src/libscotch/library_dgraph_order_io_f.c:67 | SCOTCH_dgraphOrderSaveMap | const SCOTCH_Dgraph * const grafptr; const SCOTCH_Dordering * const ordeptr; int * const fileptr; int * const revaptr |
| dgraphordersavetree | src/libscotch/library_dgraph_order_io_f.c:103 | SCOTCH_dgraphOrderSaveTree | const SCOTCH_Dgraph * const grafptr; const SCOTCH_Dordering * const ordeptr; int * const fileptr; int * const revaptr |
| dgraphorderperm | src/libscotch/library_dgraph_order_perm_f.c:68 | SCOTCH_dgraphOrderPerm | const SCOTCH_Dgraph * const grafptr; const SCOTCH_Dordering * const ordeptr; SCOTCH_Num * const permloctab; int * const revaptr |
| dgraphordercblkdist | src/libscotch/library_dgraph_order_tree_dist_f.c:68 | SCOTCH_dgraphOrderCblkDist | SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const ordeptr; SCOTCH_Num * const cblkglbptr |
| dgraphordertreedist | src/libscotch/library_dgraph_order_tree_dist_f.c:82 | SCOTCH_dgraphOrderTreeDist | SCOTCH_Dgraph * const grafptr; SCOTCH_Dordering * const ordeptr; SCOTCH_Num * const treeglbtab; SCOTCH_Num * const sizeglbtab; int * const revaptr |
| dgraphredist | src/libscotch/library_dgraph_redist_f.c:69 | SCOTCH_dgraphRedist | SCOTCH_Dgraph * const srcgrafptr; const SCOTCH_Num * const partloctab; const SCOTCH_Num * const permgsttab; const SCOTCH_Num * const vertlocdlt; const SCOTCH_Num * const edgelocdlt; SCOTCH_Dgraph * const dstgrafptr; int * const revaptr |
| dgraphscatter | src/libscotch/library_dgraph_scatter_f.c:72 | SCOTCH_dgraphScatter | SCOTCH_Dgraph * const dgrfptr; SCOTCH_Graph * const cgrfptr; int * const revaptr |
| Dgraphstat | src/libscotch/library_dgraph_stat_f.c:71 | SCOTCH_dgraphStat | const SCOTCH_Dgraph * const grafptr; SCOTCH_Num * const velominptr; SCOTCH_Num * const velomaxptr; SCOTCH_Num * const velosumptr; double * veloavgptr; double * velodltptr; SCOTCH_Num * const degrminptr; SCOTCH_Num * const degrmaxptr; double * degravgptr; double * degrdltptr; SCOTCH_Num * const edlominptr; SCOTCH_Num * const edlomaxptr; SCOTCH_Num * const edlosumptr; double * edloavgptr; double * edlodltptr; int * const revaptr |
| dmeshbuildadm | src/libscotch/library_dmesh_build_adm_f.c:71 | SCOTCH_dmeshBuildAdm | SCOTCH_Dmesh * const meshptr; const SCOTCH_Num * const baseval; const SCOTCH_Num * const velmlocnbr; SCOTCH_Num * const velmloctab; const SCOTCH_Num * const eelmlocnbr; SCOTCH_Num * const eelmloctab; const SCOTCH_Num * const vnodglbnbr; int * const revaptr |
| dmeshdgraphdual | src/libscotch/library_dmesh_dgraph_f.c:68 | SCOTCH_dmeshDgraphDual | const SCOTCH_Dmesh * const meshptr; SCOTCH_Dgraph * const grafptr; const SCOTCH_Num * const nocoptr; int * const revaptr |
| dmeshinit | src/libscotch/library_dmesh_f.c:67 | SCOTCH_dmeshInit | SCOTCH_Dmesh * const meshptr; const MPI_Fint * const commptr; int * const revaptr |
| dmeshexit | src/libscotch/library_dmesh_f.c:84 | SCOTCH_dmeshExit | SCOTCH_Dmesh * const meshptr |
| dmeshsizeof | src/libscotch/library_dmesh_f.c:96 | SCOTCH_dmeshSizeof | int * const sizeptr |
| dmeshsize | src/libscotch/library_dmesh_f.c:108 | SCOTCH_dmeshSize | const SCOTCH_Dmesh * const meshptr; SCOTCH_Num * const velmglbptr; SCOTCH_Num * const velmlocptr; SCOTCH_Num * const eelmglbptr; SCOTCH_Num * const eelmlocptr; SCOTCH_Num * const vnodglbptr |
| dmeshdata | src/libscotch/library_dmesh_f.c:125 | SCOTCH_dmeshData | const SCOTCH_Dmesh * const meshptr; const SCOTCH_Num * const indxptr; SCOTCH_Num * const baseptr; SCOTCH_Num * const velmglbptr; SCOTCH_Num * const velmlocptr; SCOTCH_Idx * const velmlocidx; SCOTCH_Num * const eelmglbptr; SCOTCH_Num * const eelmlocptr; SCOTCH_Idx * const eelmlocidx; SCOTCH_Num * const vnodglbptr; MPI_Fint * const commptr |
| dmeshload | src/libscotch/library_dmesh_io_load_f.c:71 | SCOTCH_dmeshLoad | SCOTCH_Dmesh * const meshptr; int * const fileptr; const SCOTCH_Num * const baseval; const SCOTCH_Num * const flagval; int * const revaptr |
| geominit | src/libscotch/library_geom_f.c:75 | SCOTCH_geomInit | SCOTCH_Geom * const geomptr; int * const revaptr |
| geomexit | src/libscotch/library_geom_f.c:88 | SCOTCH_geomExit | SCOTCH_Geom * const geomptr |
| geomsizeof | src/libscotch/library_geom_f.c:100 | SCOTCH_geomSizeof | int * const sizeptr |
| geomdata | src/libscotch/library_geom_f.c:112 | SCOTCH_geomData | const SCOTCH_Geom * const geomptr; const double * const indxptr; SCOTCH_Num * const dimnptr; SCOTCH_Idx * const geomidx |
| graphbase | src/libscotch/library_graph_base_f.c:71 | SCOTCH_graphBase | SCOTCH_Graph * const grafptr; const SCOTCH_Num * const basenew; SCOTCH_Num * const baseold |
| graphcheck | src/libscotch/library_graph_check_f.c:73 | SCOTCH_graphCheck | const SCOTCH_Graph * const grafptr; int * const revaptr |
| graphcoarsen | src/libscotch/library_graph_coarsen_f.c:71 | SCOTCH_graphCoarsen | SCOTCH_Graph * const finegrafptr; const SCOTCH_Num * const coarvertptr; const double * const coarnbr; const SCOTCH_Num * const flagval; SCOTCH_Graph * const coargrafptr; SCOTCH_Num * const coarmulttab; int * const revaptr |
| graphcoarsenmatch | src/libscotch/library_graph_coarsen_f.c:89 | SCOTCH_graphCoarsenMatch | SCOTCH_Graph * const finegrafptr; SCOTCH_Num * const coarvertptr; const double * const coarnbr; const SCOTCH_Num * const flagval; SCOTCH_Num * const finematetab; int * const revaptr |
| graphcoarsenbuild | src/libscotch/library_graph_coarsen_f.c:106 | SCOTCH_graphCoarsenBuild | SCOTCH_Graph * const finegrafptr; SCOTCH_Num * const coarvertptr; SCOTCH_Num * const finematetab; SCOTCH_Graph * const coargrafptr; SCOTCH_Num * const coarmulttab; int * const revaptr |
| graphcolor | src/libscotch/library_graph_color_f.c:69 | SCOTCH_graphColor | const SCOTCH_Graph * const grafptr; SCOTCH_Num * const colotab; SCOTCH_Num * const coloptr; const SCOTCH_Num * const flagval; int * const revaptr |
| graphdiampv | src/libscotch/library_graph_diam_f.c:69 | SCOTCH_graphDiamPV | SCOTCH_Graph * const grafptr; SCOTCH_Num * const diamptr |
| graphinit | src/libscotch/library_graph_f.c:79 | SCOTCH_graphInit | SCOTCH_Graph * const grafptr; int * const revaptr |
| graphexit | src/libscotch/library_graph_f.c:92 | SCOTCH_graphExit | SCOTCH_Graph * const grafptr |
| graphfree | src/libscotch/library_graph_f.c:104 | SCOTCH_graphFree | SCOTCH_Graph * const grafptr |
| graphsizeof | src/libscotch/library_graph_f.c:116 | SCOTCH_graphSizeof | int * const sizeptr |
| graphload | src/libscotch/library_graph_f.c:132 | SCOTCH_graphLoad | SCOTCH_Graph * const grafptr; int * const fileptr; const SCOTCH_Num * const baseval; const SCOTCH_Num * const flagval; int * const revaptr |
| graphsave | src/libscotch/library_graph_f.c:169 | SCOTCH_graphSave | const SCOTCH_Graph * const grafptr; int * const fileptr; int * const revaptr |
| graphbuild | src/libscotch/library_graph_f.c:204 | SCOTCH_graphBuild | SCOTCH_Graph * const grafptr; const SCOTCH_Num * const baseval; const SCOTCH_Num * const vertnbr; const SCOTCH_Num * const verttab; const SCOTCH_Num * const vendtab; const SCOTCH_Num * const velotab; const SCOTCH_Num * const vlbltab; const SCOTCH_Num * const edgenbr; const SCOTCH_Num * const edgetab; const SCOTCH_Num * const edlotab; int * const revaptr |
| graphsize | src/libscotch/library_graph_f.c:229 | SCOTCH_graphSize | const SCOTCH_Graph * const grafptr; SCOTCH_Num * const vertptr; SCOTCH_Num * const edgeptr |
| graphdata | src/libscotch/library_graph_f.c:243 | SCOTCH_graphData | const SCOTCH_Graph * const grafptr; const SCOTCH_Num * const indxptr; SCOTCH_Num * const baseptr; SCOTCH_Num * const vertptr; SCOTCH_Idx * const vertidx; SCOTCH_Idx * const vendidx; SCOTCH_Idx * const veloidx; SCOTCH_Idx * const vlblidx; SCOTCH_Num * const edgeptr; SCOTCH_Idx * const edgeidx; SCOTCH_Idx * const edloidx |
| graphstat | src/libscotch/library_graph_f.c:281 | SCOTCH_graphStat | const SCOTCH_Graph * const grafptr; SCOTCH_Num * const velominptr; SCOTCH_Num * const velomaxptr; SCOTCH_Num * const velosumptr; double * veloavgptr; double * velodltptr; SCOTCH_Num * const degrminptr; SCOTCH_Num * const degrmaxptr; double * degravgptr; double * degrdltptr; SCOTCH_Num * const edlominptr; SCOTCH_Num * const edlomaxptr; SCOTCH_Num * const edlosumptr; double * edloavgptr; double * edlodltptr |
| graphinducelist | src/libscotch/library_graph_induce_f.c:69 | SCOTCH_graphInduceList | SCOTCH_Graph * restrict const orggrafptr; const SCOTCH_Num * vnumnbr; const SCOTCH_Num * restrict const vnumtab; SCOTCH_Graph * restrict const indgrafptr; int * const revaptr |
| graphinducepart | src/libscotch/library_graph_induce_f.c:85 | SCOTCH_graphInducePart | SCOTCH_Graph * restrict const orggrafptr; const SCOTCH_Num * vnumnbr; const SCOTCH_GraphPart2 * restrict const parttab; const SCOTCH_GraphPart2 * partval; SCOTCH_Graph * restrict const indgrafptr; int * const revaptr |
| graphgeomloadchac | src/libscotch/library_graph_io_chac_f.c:73 | SCOTCH_graphGeomLoadChac | SCOTCH_Graph * const grafptr; SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| graphgeomsavechac | src/libscotch/library_graph_io_chac_f.c:128 | SCOTCH_graphGeomSaveChac | const SCOTCH_Graph * const grafptr; const SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| graphgeomloadhabo | src/libscotch/library_graph_io_habo_f.c:73 | SCOTCH_graphGeomLoadHabo | SCOTCH_Graph * const grafptr; SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| graphgeomloadmmkt | src/libscotch/library_graph_io_mmkt_f.c:73 | SCOTCH_graphGeomLoadMmkt | SCOTCH_Graph * const grafptr; SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| graphgeomsavemmkt | src/libscotch/library_graph_io_mmkt_f.c:128 | SCOTCH_graphGeomSaveMmkt | const SCOTCH_Graph * const grafptr; const SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| graphgeomloadscot | src/libscotch/library_graph_io_scot_f.c:73 | SCOTCH_graphGeomLoadScot | SCOTCH_Graph * const grafptr; SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| graphgeomsavescot | src/libscotch/library_graph_io_scot_f.c:128 | SCOTCH_graphGeomSaveScot | const SCOTCH_Graph * const grafptr; const SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| graphmapinit | src/libscotch/library_graph_map_f.c:77 | SCOTCH_graphMapInit | const SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr; const SCOTCH_Arch * const archptr; SCOTCH_Num * const mapptab; int * const revaptr |
| graphmapexit | src/libscotch/library_graph_map_f.c:93 | SCOTCH_graphMapExit | const SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr |
| graphmapcompute | src/libscotch/library_graph_map_f.c:106 | SCOTCH_graphMapCompute | SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr; SCOTCH_Strat * const straptr; int * const revaptr |
| graphmapfixedcompute | src/libscotch/library_graph_map_f.c:121 | SCOTCH_graphMapFixedCompute | SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr; SCOTCH_Strat * const straptr; int * const revaptr |
| graphremapcompute | src/libscotch/library_graph_map_f.c:136 | SCOTCH_graphRemapCompute | SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr; SCOTCH_Mapping * const mapoptr; const double * const emraptr; const SCOTCH_Num * const vmlotab; SCOTCH_Strat * const straptr; int * const revaptr |
| graphremapfixedcompute | src/libscotch/library_graph_map_f.c:154 | SCOTCH_graphRemapFixedCompute | SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr; SCOTCH_Mapping * const mapoptr; const double * const emraptr; const SCOTCH_Num * const vmlotab; SCOTCH_Strat * const straptr; int * const revaptr |
| graphmap | src/libscotch/library_graph_map_f.c:172 | SCOTCH_graphMap | SCOTCH_Graph * const grafptr; const SCOTCH_Arch * const archptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| graphmapfixed | src/libscotch/library_graph_map_f.c:188 | SCOTCH_graphMapFixed | SCOTCH_Graph * const grafptr; const SCOTCH_Arch * const archptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| graphremap | src/libscotch/library_graph_map_f.c:204 | SCOTCH_graphRemap | SCOTCH_Graph * const grafptr; const SCOTCH_Arch * const archptr; SCOTCH_Num * const parotab; const double * const emraptr; const SCOTCH_Num * const vmlotab; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| graphremapfixed | src/libscotch/library_graph_map_f.c:223 | SCOTCH_graphRemapFixed | SCOTCH_Graph * const grafptr; const SCOTCH_Arch * const archptr; SCOTCH_Num * const parotab; const double * const emraptr; const SCOTCH_Num * const vmlotab; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| graphpart | src/libscotch/library_graph_map_f.c:242 | SCOTCH_graphPart | SCOTCH_Graph * const grafptr; const SCOTCH_Num * const partptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| graphpartfixed | src/libscotch/library_graph_map_f.c:258 | SCOTCH_graphPartFixed | SCOTCH_Graph * const grafptr; const SCOTCH_Num * const partptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| graphrepart | src/libscotch/library_graph_map_f.c:274 | SCOTCH_graphRepart | SCOTCH_Graph * const grafptr; const SCOTCH_Num * const partptr; SCOTCH_Num * const parotab; const double * const emraptr; const SCOTCH_Num * const vmlotab; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| graphrepartfixed | src/libscotch/library_graph_map_f.c:293 | SCOTCH_graphRepartFixed | SCOTCH_Graph * const grafptr; const SCOTCH_Num * const partptr; SCOTCH_Num * const parotab; const double * const emraptr; const SCOTCH_Num * const vmlotab; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| stratgraphmap | src/libscotch/library_graph_map_f.c:312 | SCOTCH_stratGraphMap | SCOTCH_Strat * const straptr; const char * const string; int * const revaptr; const int strnbr |
| stratgraphmapbuild | src/libscotch/library_graph_map_f.c:339 | SCOTCH_stratGraphMapBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const SCOTCH_Num * const partnbr; const double * const kbalval; int * const revaptr |
| stratgraphclusterbuild | src/libscotch/library_graph_map_f.c:355 | SCOTCH_stratGraphClusterBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const SCOTCH_Num * const pwgtval; const double * const densval; const double * const bbalval; int * const revaptr |
| graphtabload | src/libscotch/library_graph_map_io_f.c:65 | SCOTCH_graphTabLoad | const SCOTCH_Graph * const grafptr; SCOTCH_Num * const parttab; const int * const fileptr; int * const revaptr |
| graphtabsave | src/libscotch/library_graph_map_io_f.c:100 | SCOTCH_graphTabSave | const SCOTCH_Graph * const grafptr; const SCOTCH_Num * const parttab; const int * const fileptr; int * const revaptr |
| graphmapload | src/libscotch/library_graph_map_io_f.c:136 | SCOTCH_graphMapLoad | const SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr; const int * const fileptr; int * const revaptr |
| graphmapsave | src/libscotch/library_graph_map_io_f.c:171 | SCOTCH_graphMapSave | const SCOTCH_Graph * const grafptr; SCOTCH_Mapping * const mappptr; const int * const fileptr; int * const revaptr |
| graphmapview | src/libscotch/library_graph_map_view_f.c:73 | SCOTCH_graphMapView | const SCOTCH_Graph * const grafptr; const SCOTCH_Mapping * const mappptr; const int * const fileptr; int * const revaptr |
| graphorderinit | src/libscotch/library_graph_order_f.c:77 | SCOTCH_graphOrderInit | const SCOTCH_Graph * const grafptr; SCOTCH_Ordering * const ordeptr; SCOTCH_Num * const permtab; SCOTCH_Num * const peritab; SCOTCH_Num * const cblkptr; SCOTCH_Num * const rangtab; SCOTCH_Num * const treetab; int * const revaptr |
| graphorderexit | src/libscotch/library_graph_order_f.c:97 | SCOTCH_graphOrderExit | const SCOTCH_Graph * const grafptr; SCOTCH_Ordering * const ordeptr |
| graphordersave | src/libscotch/library_graph_order_f.c:110 | SCOTCH_graphOrderSave | const SCOTCH_Graph * const grafptr; const SCOTCH_Ordering * const ordeptr; int * const fileptr; int * const revaptr |
| graphordersavemap | src/libscotch/library_graph_order_f.c:145 | SCOTCH_graphOrderSaveMap | const SCOTCH_Graph * const grafptr; const SCOTCH_Ordering * const ordeptr; int * const fileptr; int * const revaptr |
| graphordersavetree | src/libscotch/library_graph_order_f.c:181 | SCOTCH_graphOrderSaveTree | const SCOTCH_Graph * const grafptr; const SCOTCH_Ordering * const ordeptr; int * const fileptr; int * const revaptr |
| graphordercompute | src/libscotch/library_graph_order_f.c:217 | SCOTCH_graphOrderCompute | SCOTCH_Graph * const grafptr; SCOTCH_Ordering * const ordeptr; SCOTCH_Strat * const straptr; int * const revaptr |
| graphordercomputelist | src/libscotch/library_graph_order_f.c:232 | SCOTCH_graphOrderComputeList | SCOTCH_Graph * const grafptr; SCOTCH_Ordering * const ordeptr; const SCOTCH_Num * listptr; const SCOTCH_Num * const listtab; SCOTCH_Strat * const straptr; int * const revaptr |
| graphorder | src/libscotch/library_graph_order_f.c:249 | SCOTCH_graphOrder | SCOTCH_Graph * const grafptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const permtab; SCOTCH_Num * const peritab; SCOTCH_Num * const cblkptr; SCOTCH_Num * const rangtab; SCOTCH_Num * const treetab; int * const revaptr |
| graphorderlist | src/libscotch/library_graph_order_f.c:269 | SCOTCH_graphOrderList | SCOTCH_Graph * const grafptr; const SCOTCH_Num * listptr; const SCOTCH_Num * const listtab; SCOTCH_Strat * const straptr; SCOTCH_Num * const permtab; SCOTCH_Num * const peritab; SCOTCH_Num * const cblkptr; SCOTCH_Num * const rangtab; SCOTCH_Num * const treetab; int * const revaptr |
| graphordercheck | src/libscotch/library_graph_order_f.c:291 | SCOTCH_graphOrderCheck | const SCOTCH_Graph * const grafptr; const SCOTCH_Ordering * const ordeptr; int * const revaptr |
| stratgraphorder | src/libscotch/library_graph_order_f.c:305 | SCOTCH_stratGraphOrder | SCOTCH_Strat * const straptr; const char * const string; int * const revaptr; const int strnbr |
| stratgraphorderbuild | src/libscotch/library_graph_order_f.c:332 | SCOTCH_stratGraphOrderBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const SCOTCH_Num * const levlnbr; const double * const kbalval; int * const revaptr |
| graphpartovl | src/libscotch/library_graph_part_ovl_f.c:69 | SCOTCH_graphPartOvl | SCOTCH_Graph * const grafptr; const SCOTCH_Num * const partptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const parttab; int * const revaptr |
| stratgraphpartovl | src/libscotch/library_graph_part_ovl_f.c:85 | SCOTCH_stratGraphPartOvl | SCOTCH_Strat * const straptr; const char * const string; int * const revaptr; const int strnbr |
| stratgraphpartovlbuild | src/libscotch/library_graph_part_ovl_f.c:112 | SCOTCH_stratGraphPartOvlBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const SCOTCH_Num * const partnbr; const double * const kbalval; int * const revaptr |
| numsizeof | src/libscotch/library_memory_f.c:70 | SCOTCH_numSizeof | int * const sizeptr |
| meshinit | src/libscotch/library_mesh_f.c:75 | SCOTCH_meshInit | SCOTCH_Mesh * const meshptr; int * const revaptr |
| meshexit | src/libscotch/library_mesh_f.c:88 | SCOTCH_meshExit | SCOTCH_Mesh * const meshptr |
| meshsizeof | src/libscotch/library_mesh_f.c:100 | SCOTCH_meshSizeof | int * const sizeptr |
| meshload | src/libscotch/library_mesh_f.c:116 | SCOTCH_meshLoad | SCOTCH_Mesh * const meshptr; int * const fileptr; const SCOTCH_Num * const baseptr; int * const revaptr |
| meshsave | src/libscotch/library_mesh_f.c:152 | SCOTCH_meshSave | const SCOTCH_Mesh * const meshptr; int * const fileptr; int * const revaptr |
| meshbuild | src/libscotch/library_mesh_f.c:187 | SCOTCH_meshBuild | SCOTCH_Mesh * const meshptr; const SCOTCH_Num * const velmbas; const SCOTCH_Num * const vnodbas; const SCOTCH_Num * const velmnbr; const SCOTCH_Num * const vnodnbr; const SCOTCH_Num * const verttab; const SCOTCH_Num * const vendtab; const SCOTCH_Num * const velotab; const SCOTCH_Num * const vnlotab; const SCOTCH_Num * const vlbltab; const SCOTCH_Num * const edgenbr; const SCOTCH_Num * const edgetab; int * const revaptr |
| meshbuildelem | src/libscotch/library_mesh_f.c:215 | SCOTCH_meshBuildElem | SCOTCH_Mesh * const meshptr; const SCOTCH_Num * const velmbas; const SCOTCH_Num * const vnodbas; const SCOTCH_Num * const velmnbr; const SCOTCH_Num * const vnodnbr; const SCOTCH_Num * const verttab; const SCOTCH_Num * const vendtab; const SCOTCH_Num * const velotab; const SCOTCH_Num * const vnlotab; const SCOTCH_Num * const vlbltab; const SCOTCH_Num * const edgenbr; const SCOTCH_Num * const edgetab; int * const revaptr |
| meshcheck | src/libscotch/library_mesh_f.c:243 | SCOTCH_meshCheck | const SCOTCH_Mesh * const meshptr; int * const revaptr |
| meshsize | src/libscotch/library_mesh_f.c:256 | SCOTCH_meshSize | const SCOTCH_Mesh * const meshptr; SCOTCH_Num * const velmnbr; SCOTCH_Num * const vnodnbr; SCOTCH_Num * const edgenbr |
| meshdata | src/libscotch/library_mesh_f.c:271 | SCOTCH_meshData | const SCOTCH_Mesh * const meshptr; const SCOTCH_Num * const indxptr; SCOTCH_Num * const velmbas; SCOTCH_Num * const vnodbas; SCOTCH_Num * const velmnbr; SCOTCH_Num * const vnodnbr; SCOTCH_Idx * const vertidx; SCOTCH_Idx * const vendidx; SCOTCH_Idx * const veloidx; SCOTCH_Idx * const vnloidx; SCOTCH_Idx * const vlblidx; SCOTCH_Num * const edgenbr; SCOTCH_Idx * const edgeidx; SCOTCH_Num * const degrnbr |
| meshgraph | src/libscotch/library_mesh_graph_f.c:73 | SCOTCH_meshGraph | const SCOTCH_Mesh * const meshptr; SCOTCH_Graph * const grafptr; int * const revaptr |
| meshgraphdual | src/libscotch/library_mesh_graph_f.c:87 | SCOTCH_meshGraphDual | const SCOTCH_Mesh * const meshptr; SCOTCH_Graph * const grafptr; const SCOTCH_Num * const nocoptr; int * const revaptr |
| meshgeomloadhabo | src/libscotch/library_mesh_io_habo_f.c:73 | SCOTCH_meshGeomLoadHabo | SCOTCH_Mesh * const meshptr; SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| meshgeomloadscot | src/libscotch/library_mesh_io_scot_f.c:73 | SCOTCH_meshGeomLoadScot | SCOTCH_Mesh * const meshptr; SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| meshgeomsavescot | src/libscotch/library_mesh_io_scot_f.c:128 | SCOTCH_meshGeomSaveScot | const SCOTCH_Mesh * const meshptr; const SCOTCH_Geom * const geomptr; const int * const filegrfptr; const int * const filegeoptr; const char * const dataptr; int * const revaptr; const int datanbr |
| meshorderinit | src/libscotch/library_mesh_order_f.c:75 | SCOTCH_meshOrderInit | const SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr; SCOTCH_Num * const permtab; SCOTCH_Num * const peritab; SCOTCH_Num * const cblkptr; SCOTCH_Num * const rangtab; SCOTCH_Num * const treetab; int * const revaptr |
| meshorderexit | src/libscotch/library_mesh_order_f.c:95 | SCOTCH_meshOrderExit | const SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr |
| meshordersave | src/libscotch/library_mesh_order_f.c:108 | SCOTCH_meshOrderSave | const SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr; int * const fileptr; int * const revaptr |
| meshordersavemap | src/libscotch/library_mesh_order_f.c:144 | SCOTCH_meshOrderSaveMap | const SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr; int * const fileptr; int * const revaptr |
| meshordersavetree | src/libscotch/library_mesh_order_f.c:180 | SCOTCH_meshOrderSaveTree | const SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr; int * const fileptr; int * const revaptr |
| meshordercompute | src/libscotch/library_mesh_order_f.c:216 | SCOTCH_meshOrderCompute | SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr; SCOTCH_Strat * const straptr; int * const revaptr |
| meshordercomputelist | src/libscotch/library_mesh_order_f.c:231 | SCOTCH_meshOrderComputeList | SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr; const SCOTCH_Num * listptr; const SCOTCH_Num * const listtab; SCOTCH_Strat * const straptr; int * const revaptr |
| meshorder | src/libscotch/library_mesh_order_f.c:248 | SCOTCH_meshOrder | SCOTCH_Mesh * const meshptr; SCOTCH_Strat * const straptr; SCOTCH_Num * const permtab; SCOTCH_Num * const peritab; SCOTCH_Num * const cblkptr; SCOTCH_Num * const rangtab; SCOTCH_Num * const treetab; int * const revaptr |
| meshorderlist | src/libscotch/library_mesh_order_f.c:268 | SCOTCH_meshOrderList | SCOTCH_Mesh * const meshptr; const SCOTCH_Num * listptr; const SCOTCH_Num * const listtab; SCOTCH_Strat * const straptr; SCOTCH_Num * const permtab; SCOTCH_Num * const peritab; SCOTCH_Num * const cblkptr; SCOTCH_Num * const rangtab; SCOTCH_Num * const treetab; int * const revaptr |
| meshordercheck | src/libscotch/library_mesh_order_f.c:290 | SCOTCH_meshOrderCheck | const SCOTCH_Mesh * const meshptr; SCOTCH_Ordering * const ordeptr; int * const revaptr |
| stratmeshorder | src/libscotch/library_mesh_order_f.c:304 | SCOTCH_stratMeshOrder | SCOTCH_Strat * const straptr; const char * const string; int * const revaptr; const int strnbr |
| stratmeshorderbuild | src/libscotch/library_mesh_order_f.c:331 | SCOTCH_stratMeshOrderBuild | SCOTCH_Strat * const straptr; const SCOTCH_Num * const flagval; const double * const balrat; int * const revaptr |
| stratinit | src/libscotch/library_parser_f.c:70 | SCOTCH_stratInit | SCOTCH_Strat * const straptr; int * const revaptr |
| stratexit | src/libscotch/library_parser_f.c:83 | SCOTCH_stratExit | SCOTCH_Strat * const straptr |
| stratfree | src/libscotch/library_parser_f.c:95 | SCOTCH_stratFree | SCOTCH_Strat * const straptr |
| stratsave | src/libscotch/library_parser_f.c:107 | SCOTCH_stratSave | SCOTCH_Strat * const straptr; int * const fileptr; int * const revaptr |
| randomload | src/libscotch/library_random_f.c:71 | SCOTCH_randomLoad | int * const fileptr; int * const revaptr |
| randomsave | src/libscotch/library_random_f.c:105 | SCOTCH_randomSave | int * const fileptr; int * const revaptr |
| randomproc | src/libscotch/library_random_f.c:139 | SCOTCH_randomProc | const int * const procnum |
| randomreset | src/libscotch/library_random_f.c:151 | SCOTCH_randomReset | void |
| randomseed | src/libscotch/library_random_f.c:162 | SCOTCH_randomSeed | const SCOTCH_Num * const seedptr |
| randomval | src/libscotch/library_random_f.c:174 | SCOTCH_randomVal | const SCOTCH_Num * const randmax; SCOTCH_Num * const revaptr |
| version | src/libscotch/library_version_f.c:71 | SCOTCH_version | int * const versptr; int * const relaptr; int * const patcptr |
| metis_meshtodual | src/libscotchmetis/metis_graph_dual_f.c:100 | SCOTCHMETISNAMES(METIS_MeshToDual) | const SCOTCH_Num * const ne; const SCOTCH_Num * const nn; const SCOTCH_Num * const eptr; const SCOTCH_Num * const eind; const SCOTCH_Num * const ncommon; const SCOTCH_Num * const nuimflag; SCOTCH_Num ** const xadj; SCOTCH_Num ** const adjncy |
| metis_meshtodual | src/libscotchmetis/metis_graph_dual_f.c:100 | SCOTCHMETISNAMES(METIS_MeshToDual) | const SCOTCH_Num * const ne; const SCOTCH_Num * const nn; const SCOTCH_Num * const eptr; const SCOTCH_Num * const eind; const SCOTCH_Num * const ncommon; const SCOTCH_Num * const nuimflag; SCOTCH_Num ** const xadj; SCOTCH_Num ** const adjncy |
| metis_v3_edgend | src/libscotchmetis/metis_graph_order_f.c:233 | SCOTCHMETISNAMES(METIS_V3_EdgeND) | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm; int * const revaptr |
| metis_v3_nodend | src/libscotchmetis/metis_graph_order_f.c:233 | SCOTCHMETISNAMES(METIS_V3_NodeND) | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm; int * const revaptr |
| metis_v3_nodewnd | src/libscotchmetis/metis_graph_order_f.c:233 | SCOTCHMETISNAMES(METIS_V3_NodeWND) | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm; int * const revaptr |
| metis_v5_nodend | src/libscotchmetis/metis_graph_order_f.c:233 | SCOTCHMETISNAMES(METIS_V5_NodeND) | const SCOTCH_Num * const nvtxs; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm; int * const revaptr |
| metis_edgend | src/libscotchmetis/metis_graph_order_f.c:233 |  | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm |
| metis_nodend | src/libscotchmetis/metis_graph_order_f.c:233 |  | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm |
| metis_nodewnd | src/libscotchmetis/metis_graph_order_f.c:233 |  | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm |
| metis_nodend | src/libscotchmetis/metis_graph_order_f.c:233 |  | const SCOTCH_Num * const nvtxs; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const options; SCOTCH_Num * const perm; SCOTCH_Num * const iperm |
| metis_partmeshdual | src/libscotchmetis/metis_graph_part_dual_f.c:111 | SCOTCHMETISNAMES(METIS_PartMeshDual) | const SCOTCH_Num * const ne; const SCOTCH_Num * const nn; const SCOTCH_Num * const eptr; const SCOTCH_Num * const eind; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const ncommon; const SCOTCH_Num * const nparts; const double * const tpwgts; const SCOTCH_Num * const options; SCOTCH_Num * const objval; SCOTCH_Num * const epart; SCOTCH_Num * const npart |
| metis_partmeshdual | src/libscotchmetis/metis_graph_part_dual_f.c:111 | SCOTCHMETISNAMES(METIS_PartMeshDual) | const SCOTCH_Num * const ne; const SCOTCH_Num * const nn; const SCOTCH_Num * const eptr; const SCOTCH_Num * const eind; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const ncommon; const SCOTCH_Num * const nparts; const double * const tpwgts; const SCOTCH_Num * const options; SCOTCH_Num * const objval; SCOTCH_Num * const epart; SCOTCH_Num * const npart |
| metis_v3_partgraphkway | src/libscotchmetis/metis_graph_part_f.c:328 | SCOTCHMETISNAMES(METIS_V3_PartGraphKway) | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const nparts; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part; int * const revaptr |
| metis_v3_partgraphrecursive | src/libscotchmetis/metis_graph_part_f.c:328 | SCOTCHMETISNAMES(METIS_V3_PartGraphRecursive) | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const nparts; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part; int * const revaptr |
| metis_v3_partgraphvkway | src/libscotchmetis/metis_graph_part_f.c:328 | SCOTCHMETISNAMES(METIS_V3_PartGraphVKway) | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const nparts; const SCOTCH_Num * const options; SCOTCH_Num * const volume; SCOTCH_Num * const part; int * const revaptr |
| metis_v5_partgraphkway | src/libscotchmetis/metis_graph_part_f.c:328 | SCOTCHMETISNAMES(METIS_V5_PartGraphKway) | const SCOTCH_Num * const nvtxs; const SCOTCH_Num * const ncon; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const nparts; const double * const tpwgts; const double * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const objval; SCOTCH_Num * const part; int * const revaptr |
| metis_v5_partgraphrecursive | src/libscotchmetis/metis_graph_part_f.c:328 | SCOTCHMETISNAMES(METIS_V5_PartGraphRecursive) | const SCOTCH_Num * const nvtxs; const SCOTCH_Num * const ncon; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const nparts; const double * const tpwgts; const double * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const objval; SCOTCH_Num * const part; int * const revaptr |
| metis_partgraphkway | src/libscotchmetis/metis_graph_part_f.c:328 |  | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const nparts; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part |
| metis_partgraphrecursive | src/libscotchmetis/metis_graph_part_f.c:328 |  | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const nparts; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part |
| metis_partgraphvkway | src/libscotchmetis/metis_graph_part_f.c:328 |  | const SCOTCH_Num * const n; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const nparts; const SCOTCH_Num * const options; SCOTCH_Num * const volume; SCOTCH_Num * const part |
| metis_partgraphkway | src/libscotchmetis/metis_graph_part_f.c:328 |  | const SCOTCH_Num * const nvtxs; const SCOTCH_Num * const ncon; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const nparts; const double * const tpwgts; const double * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const objval; SCOTCH_Num * const part |
| metis_partgraphrecursive | src/libscotchmetis/metis_graph_part_f.c:328 |  | const SCOTCH_Num * const nvtxs; const SCOTCH_Num * const ncon; const SCOTCH_Num * const xadj; const SCOTCH_Num * const adjncy; const SCOTCH_Num * const vwgt; const SCOTCH_Num * const vsize; const SCOTCH_Num * const adjwgt; const SCOTCH_Num * const nparts; const double * const tpwgts; const double * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const objval; SCOTCH_Num * const part |
| metis_setdefaultoptions | src/libscotchmetis/metis_options_f.c:86 | SCOTCHMETISNAMES(METIS_SetDefaultOptions) | SCOTCH_Num * const options |
| metis_setdefaultoptions | src/libscotchmetis/metis_options_f.c:86 | SCOTCHMETISNAMES(METIS_SetDefaultOptions) | SCOTCH_Num * const options |
| parmetis_v3_mesh2dual | src/libscotchmetis/parmetis_dgraph_dual_f.c:111 | SCOTCHMETISNAMES(ParMETIS_V3_Mesh2Dual) | const SCOTCH_Num * const elmdist; SCOTCH_Num * const eptr; SCOTCH_Num * const eind; const SCOTCH_Num * const numflag; const SCOTCH_Num * const ncommonnodes; SCOTCH_Num ** xadj; SCOTCH_Num ** adjncy; const MPI_Fint * const commptr; int * const revaptr |
| parmetis_v3_mesh2dual | src/libscotchmetis/parmetis_dgraph_dual_f.c:111 | SCOTCHMETISNAMES(ParMETIS_V3_Mesh2Dual) | const SCOTCH_Num * const elmdist; SCOTCH_Num * const eptr; SCOTCH_Num * const eind; const SCOTCH_Num * const numflag; const SCOTCH_Num * const ncommonnodes; SCOTCH_Num ** xadj; SCOTCH_Num ** adjncy; const MPI_Fint * const commptr |
| parmetis_v3_nodend | src/libscotchmetis/parmetis_dgraph_order_f.c:117 | SCOTCHMETISNAMES(ParMETIS_V3_NodeND) | const SCOTCH_Num * const vtxdist; SCOTCH_Num * const xadj; SCOTCH_Num * const adjncy; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const order; SCOTCH_Num * const sizes; const MPI_Fint * const commptr; int * const revaptr |
| parmetis_v3_nodend | src/libscotchmetis/parmetis_dgraph_order_f.c:117 | SCOTCHMETISNAMES(ParMETIS_V3_NodeND) | const SCOTCH_Num * const vtxdist; SCOTCH_Num * const xadj; SCOTCH_Num * const adjncy; const SCOTCH_Num * const numflag; const SCOTCH_Num * const options; SCOTCH_Num * const order; SCOTCH_Num * const sizes; const MPI_Fint * const commptr |
| parmetis_v3_partkway | src/libscotchmetis/parmetis_dgraph_part_f.c:198 | SCOTCHMETISNAMES(ParMETIS_V3_PartKway) | const SCOTCH_Num * const vtxdist; SCOTCH_Num * const xadj; SCOTCH_Num * const adjncy; SCOTCH_Num * const vwgt; SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const ncon; const SCOTCH_Num * const nparts; const float * const tpwgts; const float * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part; const MPI_Fint * const commptr; int * const revaptr |
| parmetis_v3_partgeomkway | src/libscotchmetis/parmetis_dgraph_part_f.c:198 | SCOTCHMETISNAMES(ParMETIS_V3_PartGeomKway) | const SCOTCH_Num * const vtxdist; SCOTCH_Num * const xadj; SCOTCH_Num * const adjncy; SCOTCH_Num * const vwgt; SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const ndims; const float * const xyz; const SCOTCH_Num * const ncon; const SCOTCH_Num * const nparts; const float * const tpwgts; const float * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part; const MPI_Fint * const commptr; int * const revaptr |
| parmetis_v3_partkway | src/libscotchmetis/parmetis_dgraph_part_f.c:198 | SCOTCHMETISNAMES(ParMETIS_V3_PartKway) | const SCOTCH_Num * const vtxdist; SCOTCH_Num * const xadj; SCOTCH_Num * const adjncy; SCOTCH_Num * const vwgt; SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const ncon; const SCOTCH_Num * const nparts; const float * const tpwgts; const float * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part; const MPI_Fint * const commptr |
| parmetis_v3_partgeomkway | src/libscotchmetis/parmetis_dgraph_part_f.c:198 | SCOTCHMETISNAMES(ParMETIS_V3_PartGeomKway) | const SCOTCH_Num * const vtxdist; SCOTCH_Num * const xadj; SCOTCH_Num * const adjncy; SCOTCH_Num * const vwgt; SCOTCH_Num * const adjwgt; const SCOTCH_Num * const wgtflag; const SCOTCH_Num * const numflag; const SCOTCH_Num * const ndims; const float * const xyz; const SCOTCH_Num * const ncon; const SCOTCH_Num * const nparts; const float * const tpwgts; const float * const ubvec; const SCOTCH_Num * const options; SCOTCH_Num * const edgecut; SCOTCH_Num * const part; const MPI_Fint * const commptr |
