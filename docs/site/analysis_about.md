# What is this?

PyScotch is half a Python binding and half an independent test bench for Scotch. This section is the second half
made public: every lead we have on Scotch 7.0.x, where it stands in each release, how we verified it, and the fixes we
propose, written to be applied as they are.

- [Dashboard](index.html) — every finding, filterable: source, status per Scotch version, severity, patch; one page per finding with evidence, fix options, trade-offs and the patch.
- [Patch series](series.html) — the combined series on v7.0.17, the apply check and the build-and-test matrix.

## How this is produced

Honestly: by AI agents, a lot of them, checked by running code rather than by a human reading every line.
Thirty agents, one per group of source files, each re-read its leads in the 7.0.17 tree, ran reproducers against
sanitizer builds (sequential and PT-Scotch), hunted for the same pattern elsewhere, wrote at least two real diffs,
and turned the recommended one into a commit built warning-free with 32-bit and 64-bit integers and run through
the relevant check targets. A combine step then proved that all the series apply together, and the whole suite was
run again on the result against a pristine baseline. The prose on each page is the agent's own, unedited.

Each lead keeps its original identifier and author. Review text is cited by identifier, never reproduced; what you
read is our own wording of the defect, its status in the given Scotch version, what we ran to check it, the location
in that version, and the fix options with their trade-offs. Everything is regenerated per Scotch release from
`upstream/reports/<version>/`, so a later release is a new column, not a new report. Mistakes are ours; the data
and the patches are there to be checked.

## Acknowledgements

François Pellegrini, for Scotch, and for turning bug reports into fixes within days. Every patch here tries to be
one you would have written; where it is not, the alternatives say why.

Robert Perry, for the review of Scotch 7.0.16. 192 precise leads gave this test bench far more to verify and fix
than it would have found alone.

PyScotch's maintainer did not write this analysis: he pointed the AI at the review, set the bar, paid the bill,
nudged when it stalled, and chose to publish. The calls that remain his are listed, not hidden.

— Claude (Fable 5.1)
