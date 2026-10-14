# G04-strategy-parser - summary

COR-01  still-present    ran  high    -> patches/0002 (+0010 test)
COR-22  still-present    ran  medium  -> patches/0001 (+0010)
COR-23  still-present    ran  low     -> patches/0003, 0004 (+0010)
COR-12  fixed-in-7.0.17  ran  medium  -> -
COR-26  still-present    ran  low     -> patches/0006 (modulus), 0007 (literals) (+0010)
COR-13  still-present    ran  medium  -> patches/0005 (+0010)
COR-25  fixed-in-7.0.17  ran  low     -> - (residual column base: PS2-2 -> patches/0008)
PS2-G04-strategy-parser-1 (duplicate strategy parameter leaks)        low  -> patches/0004
PS2-G04-strategy-parser-2 (0-based columns after a newline)           info -> patches/0008
PS2-G04-strategy-parser-3 (NULL strategy defaults crash b/n methods)  high -> patches/0009  (touches bgraph_bipart_st.c, bdgraph_bipart_st.c, hdgraph_order_st.c)
PS2-G04-strategy-parser-4 (last_resort parser_yy.c stale)             info -> no patch
PS2-G04-strategy-parser-5 (%lf loses precision in saved tests)        info -> no patch

Series: 10 commits on v7.0.17 (patches/), git am clean on a fresh clone, every commit compiles its files with 0 warnings/conflicts
(bison 3.8.2, flex 2.6.4), full 32-bit and 64-bit ASan+UBSan builds with 0 warnings; check_strat_seq (+new cases), check_strat_par,
check_scotch_graph_map, check_scotch_graph_order pass; stylecheck.py and git diff --check report nothing new.

Three most important facts
1. COR-01/22/23 are one design: bison discards mid-rule and stack values on error recovery. Fix = typed <SAVE> value + %destructor that
   frees the in-progress method node and restores the enclosing context, %destructor for <STRAT>/<TEST>, type check via YYERROR into the
   existing error rule. Mutation fuzz: 2072/2400 sanitizer hits on pristine (1853 leaks, 185 NULL derefs, 4 misaligned Strat* stores,
   2 stratSave crashes) -> 0/2400 (two seeds) after the series. The first pass's NULL-guard would leave stale-context messages and leaks.
2. COR-13: differential tester (random ASTs, structural tree compare) 942/2000 wrong round-trips on pristine -> 0/5000 patched. Chosen fix
   = always parenthesise operands (his stratSave style; simple tests keep their exact pristine text); the review's row swap is insufficient.
3. New high: `gmap ... -Mr{sep=m{asc=b,low=b}}` (valid string) crashes in bgraphBipartSt because bgraph/bdgraph `b` and hdgraph `n` lack a
   &stratdummy default for one strategy parameter (parser only warns). One-line table fixes (commit 9) are outside this group's files.

Could not do / decisions for the user
- last_resort regeneration: not included. The maintainer regenerates separately at release time (38cbde4); his flex output differs from
  local flex 2.6.4 only by #line numbers (one lower), so a local regeneration is not byte-identical to his. Note last_resort/parser_yy.c is
  already stale upstream (PS2-4). Series requires bison >= 3.6 for YYerror and >= 3.1 for typed mid-rules; CMake pins 3.8.2 (src/CMakeLists.txt:83).
- Commit 9 touches three non-parser files: check for collisions with the bgraph/bdgraph/hdgraph groups before sending.
- Behaviour changes to confirm: error messages for nested errors now name the enclosing parameter; integer literal overflow is an error
  (was silent); `m{vert=}` is rejected (was accepted); unset band `org` now means the empty strategy instead of a crash.
- Double-constant precision (PS2-5) and the fmod(x,0)=NaN case are reported, not patched (format/semantics decisions).
