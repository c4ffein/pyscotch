"""Construction-time checking of PT-Scotch (distributed) strategy strings.

The sequential grammars have had a probe since 7.0.1; this is its twin for
the dmapping/dordering grammars, wired into set_dgraph_mapping/ordering and
into Strategy(string) when the parallel library is loaded. Classifications
below were established empirically on 7.0.15 (one process per probe):

    dmapping : "m" invalid, "r" hollow, Build-canonical ok
    dordering: "q" hollow, "s" ok, "n" parses but SCOTCH_stratSave SEGFAULTS
               (upstream bug, see QUESTIONS_FOR_SCOTCH_TEAM.md) -> the probe
               sandboxes the save step and classifies the crash as hollow.
"""

from ctypes import byref, c_double

import pytest

from pyscotch import Strategy, libscotch as lib
from pyscotch.strategy import _ephemeral_strat, _probe_dgraph_string, _saved_form

pytestmark = pytest.mark.skipif(not lib.is_parallel(), reason="needs the parallel (PT-Scotch) library")


def canonical_dmapping():
    with _ephemeral_strat() as s:
        rc = lib.SCOTCH_stratDgraphMapBuild(
            byref(s), lib.SCOTCH_Num(0), lib.SCOTCH_Num(2), lib.SCOTCH_Num(4), c_double(0.01)
        )
        assert rc == 0
        return _saved_form(s).strip()


class TestDgraphProbe:
    @pytest.mark.parametrize(
        "string,expected",
        [
            ("m", {"dmapping": "invalid", "dordering": "invalid"}),
            ("r", {"dmapping": "hollow", "dordering": "invalid"}),
            ("q", {"dmapping": "invalid", "dordering": "hollow"}),
            ("s", {"dmapping": "invalid", "dordering": "ok"}),
            ("garbage{", {"dmapping": "invalid", "dordering": "invalid"}),
        ],
    )
    def test_matrix(self, string, expected):
        assert _probe_dgraph_string(string) == expected

    def test_bare_n_is_hollow_via_the_sandbox(self):
        """ "n" parses under dordering but stratSave crashes upstream; the
        sandboxed probe must survive and report hollow, never kill us."""
        assert _probe_dgraph_string("n") == {"dmapping": "invalid", "dordering": "hollow"}

    def test_canonical_mapping_is_ok(self):
        assert _probe_dgraph_string(canonical_dmapping())["dmapping"] == "ok"


class TestSettersFailFast:
    def test_hollow_mapping_rejected(self):
        with pytest.raises(ValueError, match="hollow"):
            Strategy().set_dgraph_mapping("r")

    def test_hollow_ordering_rejected_even_when_upstream_save_crashes(self):
        with pytest.raises(ValueError, match="hollow"):
            Strategy().set_dgraph_ordering("n")

    def test_invalid_rejected_with_grammar_hint(self):
        with pytest.raises(ValueError, match="does not parse"):
            Strategy().set_dgraph_mapping("garbage{")

    def test_valid_strings_accepted(self):
        s = Strategy()
        s.set_dgraph_mapping(canonical_dmapping())
        Strategy().set_dgraph_ordering("s")

    def test_empty_string_stays_verbatim(self):
        """Documented exception: "" is passed through (do-nothing method)."""
        Strategy().set_dgraph_mapping("")
        Strategy().set_dgraph_ordering("")


class TestConstructorUnderParallelLibrary:
    def test_distributed_string_accepted(self):
        """Before: a PT-Scotch-only string failed with 'parses under none' —
        the constructor only knew the sequential grammars."""
        Strategy(canonical_dmapping())

    def test_bare_m_still_rejected(self):
        with pytest.raises(ValueError):
            Strategy("m")

    def test_garbage_names_all_five_grammars(self):
        with pytest.raises(ValueError, match="dmapping, dordering"):
            Strategy("garbage{")


class TestParserFaultIsContained:
    """Upstream's parser faults on a syntax error inside a strategy-valued
    parameter (QUESTIONS: `r{sep=m{}}` and friends). The sandboxed probe must
    turn that into a plain ValueError — the caller's process never parses
    such a string in-process."""

    @pytest.mark.parametrize("string", ["r{sep=m{}}", "r{sep=(}", "r{sep=(m}"])
    def test_malformed_nested_strategy_raises_cleanly(self, string):
        probe = _probe_dgraph_string(string)
        assert probe == {"dmapping": "invalid", "dordering": "invalid"}, probe
        with pytest.raises(ValueError, match="does not parse"):
            Strategy().set_dgraph_mapping(string)


class TestDistributedSaveParseSaveIdempotence:
    """Same oracle check for the distributed grammars (Build-made strategies
    are the only complete ones we can obtain without hand-writing them)."""

    def test_dgraph_mapping(self):
        from ctypes import c_char_p

        saved = canonical_dmapping()
        with _ephemeral_strat() as s:
            assert lib.SCOTCH_stratDgraphMap(byref(s), c_char_p(saved.encode())) == 0
            assert _saved_form(s).strip() == saved

    def test_dgraph_ordering(self):
        from ctypes import c_char_p

        with _ephemeral_strat() as s:
            assert (
                lib.SCOTCH_stratDgraphOrderBuild(
                    byref(s), lib.SCOTCH_Num(0), lib.SCOTCH_Num(2), lib.SCOTCH_Num(0), c_double(0.2)
                )
                == 0
            )
            saved = _saved_form(s).strip()
        with _ephemeral_strat() as s:
            assert lib.SCOTCH_stratDgraphOrder(byref(s), c_char_p(saved.encode())) == 0
            assert _saved_form(s).strip() == saved
