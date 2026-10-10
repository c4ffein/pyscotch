# Test data

`m16x16_b100000_v.grf` — Scotch's own 16x16 grid test graph (base 100000,
vertex weights), copied verbatim from `src/check/data/` of the Scotch
distribution (© Inria, CeCILL-C licence, as the rest of Scotch). It is the
reproducibility harness's reference input: the graph on which the 7.0.16
threaded-`bgraphBipartGg()` nondeterminism shows up as different cuts
(QUESTIONS_FOR_SCOTCH_TEAM.md, 2026-10-08). Vendored so the harness runs
anywhere — not every upstream release tarball ships this file (older ones do
not), and CI builds Scotch from tarballs without the submodule.
