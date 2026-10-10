# Tasks

## Known-degenerate bare strategy letters — pending François's answer

The PyScotch side is done: `Strategy("m")` (and any hollow string) is rejected
at construction (see DONE 2026-07-31 below), while `set_mapping("m")` keeps
the verbatim degenerate Scotch semantics, pinned by
`TestBrokenBareStringsStayExplicit`. What remains is upstream-dependent,
per the grammar question in QUESTIONS_FOR_SCOTCH_TEAM.md:

- If upstream makes bare letters build real defaults: PyScotch inherits for
  free (strings pass through verbatim); delete `test_bare_m_is_still_degenerate`
  and the degenerate half of
  `test_incomplete_complex_string_is_degenerate_but_complete_works` when they
  turn red, unskip `test_future_incomplete_strategies_no_longer_silent`, and
  loosen the constructor's hollow rejection to match the new semantics.
- Do NOT silently rewrite bare letters to full strings: same string must not
  mean different things in PyScotch vs C Scotch. (No exceptions since the
  2026-07-28 reversal: `""` is passed verbatim too; `None` is the default.)

## Custom strategy-string parser (replace flex/bison) — Phase 2

Phase-1 spike DONE (see below): a hand-written recursive-descent front-end
(`experiments/parser-rd/parser_rd.c`) is byte-for-byte equivalent to the
bison parser on all valid strings. Remaining work, gated on a conversation
with François (see the two new QUESTIONS entries — the parser CRASHes on
malformed nested strategies, and the empty-scalar-value over-acceptance):

- **Phase 2a — error transport.** The reason to do this at all: return
  structured diagnostics (position, expected tokens, partial parse) to the
  caller instead of the `SCOTCH_errorPrint` stderr side channel + 0/NULL.
  The RD parser already tracks positions; they just need to reach the API.
  Old API (0/nonzero + errorPrint) stays; richer errors are additive.
- **Phase 2b — the two trap fixes**, each a separate reviewable change since
  they flip accept/reject: reject `f{move=}`-style empty scalar values;
  fix the `PARAMVAL:error` NULL-deref crash. Decide with upstream first.
- **Parallel grammars.** The spike covers the four sequential tables; add the
  `dgraph` mapping/ordering grammars.
- **Upstream integration path.** Keep `parser_yy.y` as the documented grammar
  with a CI differential test in Scotch's own suite, or replace it outright?
  Counter-offer the former if they treat the `.y` as the spec. Develop as a
  patch series against `build/scotch-src` and run PyScotch's full suite +
  the fuzzer against it before proposing anything.

## Typed strategy-grammar builder — remaining scope

The builder shipped (see DONE 2026-07-31); still open, in order of value:

- DONE 2026-10-09: importer (`strategy_grammar.parse`) + dgraph families
  (`DMapping`/`DBipart`/`DOrdering`/`DSeparation`) + the agreement tests on
  every Scotch default. Still open: mesh grammar families (`hmesh_order_st.c`,
  `vmesh_separate_st.c`), and modelling condition tests beyond opaque text.
- Review the design against François's reply on bare-letter semantics before
  extending it (robust to either answer, but worth the look).

## DEFERRED 2026-10-09 — dual-variant wheels (pristine + behavioral-patched)

Trigger to build it: upstream does not fix a behavioral regression within a
release cycle, OR a second behavioral patch enters `_BEHAVIORAL_PATCHES`.
Until then the answer to a defective upstream release is the pin, not a fork:
`_SKIPPED_VERSIONS` + `_SHIPPED_VERSION` stay on the newest release that
passes `make test-reproducibility` (the bump gate), and the `release-watch`
CI job mails when upstream moves.

Design if/when triggered (catalog-driven, self-retiring):
- Wheel bundles `lib{32,64}/` (pristine) AND `lib{32,64}-patched/` only when
  the shipped version has behavioral patches; single-variant otherwise.
- `PYSCOTCH_SCOTCH_VARIANT=upstream|patched`, default `patched` when one
  exists; an explicit choice is silent, the auto-selected patched variant
  emits ONE `RuntimeWarning` per process (filterable), and `doctor` always
  prints a `Variant:` line + `pyscotch.scotch_patches()` exposes the list.
- Dev build (`scotch-builds/`) mirrors the layout so the differential tier
  keeps comparing pristine vs a pristine gpart while the reproducibility
  harness audits the patched variant.
- Cost: wheel size x2 (~1.4 MB), two Scotch compiles per int width in the
  manylinux job (aarch64 under emulation ~doubles).
