"""
Tests for Scotch error-message capture (SCOTCH_errorPrint interposition).

pyscotch.libscotch loads libpyscotch_compat.so before the Scotch libraries so
that Scotch's error/warning printers are interposed and their messages are
captured instead of going to stderr. Failed wrapper calls then raise
RuntimeError via lib.scotch_error(), with the captured Scotch messages
appended to the exception text.
"""

import ctypes

import pytest

from pyscotch import libscotch as lib
from pyscotch.strategy import Strategy

# Capture is only available with PyScotch's own builds (libpyscotch_compat.so);
# with a system-installed Scotch, messages keep going to stderr.
capture_available = pytest.mark.skipif(
    lib._err_capture is None,
    reason="error capture unavailable (system Scotch, no libpyscotch_compat.so)",
)


@capture_available
class TestErrorCapture:
    def test_invalid_mapping_strategy_includes_scotch_message(self):
        """A bad strategy string must surface Scotch's own parser error."""
        strategy = Strategy()
        with pytest.raises(RuntimeError) as excinfo:
            strategy.set_mapping("this-is-not-a-strategy((")
        message = str(excinfo.value)
        # Context and error code from the wrapper...
        assert "Failed to set mapping strategy" in message
        assert "(error code: 1)" in message
        # ...plus the captured Scotch parser diagnostic — the whole point.
        assert "stratParserParse" in message

    def test_invalid_ordering_strategy_includes_scotch_message(self):
        strategy = Strategy()
        with pytest.raises(RuntimeError) as excinfo:
            strategy.set_ordering("not-an-ordering-strategy((")
        assert "stratParserParse" in str(excinfo.value)

    def test_get_scotch_messages_clears_by_default(self):
        strategy = Strategy()
        with pytest.raises(RuntimeError):
            strategy.set_mapping("this-is-not-a-strategy((")
        # scotch_error() already consumed the messages when raising, and a
        # subsequent read (after clear) must return the empty string.
        assert lib.get_scotch_messages() == ""

    def test_get_scotch_messages_clear_false_preserves_messages(self):
        strategy = Strategy()
        try:
            lib.SCOTCH_stratGraphMap(ctypes.byref(strategy._strat), b"this-is-not-a-strategy((")
            first = lib.get_scotch_messages(clear=False)
            assert "stratParserParse" in first
            second = lib.get_scotch_messages()  # clear=True
            assert second == first
            assert lib.get_scotch_messages() == ""
        finally:
            strategy.close()

    def test_successful_operation_leaves_no_captured_errors(self):
        lib.get_scotch_messages()  # start from a clean slate
        strategy = Strategy()
        strategy.set_mapping("")  # valid parse: Scotch's do-nothing strategy
        strategy.close()
        assert lib.get_scotch_messages() == ""
