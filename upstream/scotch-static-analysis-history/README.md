# Static analysis history

Dated snapshots of large, agent-driven static reads of the Scotch sources.
One directory per run: `<model>_<YYYY-MM-DD>/`, the files exactly as the run
produced them.

**Read these as leads, not findings.** A static read is not proof: each run's
own synthesis says so. Only entries that were later *reproduced* against a
built library graduate to `../QUESTIONS_FOR_SCOTCH_TEAM.md`; everything else
here is a backlog to triage through PyScotch's oracles (see `../README.md`),
and some leads will already be fixed or moot by the time anyone reads them.

| Run | Scotch analysed | Scope | Notes |
|---|---|---|---|
| `claude_2026-07-13/` | 7.0.11 (7.0.12 just released) | twelve parallel analysts over `libscotch` (~114k LOC), the METIS/esmumps/CLI ecosystem and `src/check`; one report per subsystem plus a synthesis | model version not recorded by the run; five already-known issues were given as calibration and excluded |
