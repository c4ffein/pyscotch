"""
libscotch.to_scotch_array and the public paths that rely on it.

Scotch reads every array through a raw pointer, so an array handed over must
be C-contiguous and of the Scotch integer width. `to_scotch_array` is the
sequential wrappers' single conversion point: it must return the caller's own
array when that already qualifies (no copy, so in-place semantics survive),
and a compacted/converted copy otherwise -- in particular for a strided view,
whose data pointer points into interleaved memory.
"""

import numpy as np
import pytest

from pyscotch import Graph
from pyscotch import libscotch as lib


def wrong_dtype():
    return np.int32 if lib.get_scotch_dtype() == np.int64 else np.int64


class TestToScotchArray:
    def test_qualifying_array_is_returned_as_is(self):
        arr = np.arange(6, dtype=lib.get_scotch_dtype())
        out, ptr = lib.to_scotch_array(arr)
        assert out is arr
        assert ptr[0] == 0 and ptr[5] == 5

    def test_wrong_width_is_converted_to_a_copy(self):
        arr = np.arange(6, dtype=wrong_dtype())
        out, _ = lib.to_scotch_array(arr)
        assert out is not arr
        assert out.dtype == lib.get_scotch_dtype()
        assert out.flags.c_contiguous
        np.testing.assert_array_equal(out, arr)

    def test_strided_view_is_compacted(self):
        """A view with a stride of two elements must not be passed as a pointer:
        Scotch would read the interleaved elements."""
        base = np.repeat(np.arange(6, dtype=lib.get_scotch_dtype()), 2)
        view = base[::2]
        assert not view.flags.c_contiguous
        out, ptr = lib.to_scotch_array(view)
        assert out.flags.c_contiguous
        assert not np.shares_memory(out, base)
        np.testing.assert_array_equal(out, np.arange(6))
        assert [ptr[i] for i in range(6)] == list(range(6))

    def test_python_list_is_accepted(self):
        out, _ = lib.to_scotch_array([3, 1, 2])
        assert isinstance(out, np.ndarray)
        assert out.dtype == lib.get_scotch_dtype()
        np.testing.assert_array_equal(out, [3, 1, 2])

    def test_copy_true_never_returns_the_caller_array(self):
        arr = np.arange(6, dtype=lib.get_scotch_dtype())
        out, _ = lib.to_scotch_array(arr, copy=True)
        assert out is not arr
        assert not np.shares_memory(out, arr)
        np.testing.assert_array_equal(out, arr)

    def test_copy_true_does_not_copy_twice(self):
        """A conversion is already a copy: copy=True must not add a second one
        (it used to), but the result must still be independent of the input."""
        arr = np.arange(6, dtype=wrong_dtype())
        out, _ = lib.to_scotch_array(arr, copy=True)
        assert out.dtype == lib.get_scotch_dtype()
        assert not np.shares_memory(out, arr)
        out[0] = 99
        assert arr[0] == 0

    def test_empty_array(self):
        out, _ = lib.to_scotch_array(np.array([], dtype=wrong_dtype()))
        assert out.dtype == lib.get_scotch_dtype()
        assert len(out) == 0


class TestStridedViewsOnPublicPaths:
    """End-to-end: strided and wrong-width arrays through methods that pass
    the caller's arrays to Scotch."""

    def test_build_from_strided_views(self, hexagon_graph):
        indptr, indices, _ = hexagon_graph._csr_arrays()
        dtype = lib.get_scotch_dtype()
        verttab_view = np.repeat(indptr.astype(dtype), 2)[::2]
        edgetab_view = np.repeat(indices.astype(dtype), 2)[::2]
        assert not verttab_view.flags.c_contiguous

        graph = Graph()
        graph.build(verttab_view, edgetab_view)
        assert graph.check() is True
        got_indptr, got_indices, _ = graph._csr_arrays()
        np.testing.assert_array_equal(got_indptr, indptr)
        np.testing.assert_array_equal(got_indices, indices)

    def test_order_check_with_strided_and_wrong_width_permutations(self, hexagon_graph):
        """order_check reads permtab/peritab through to_scotch_array. A strided
        view of a valid ordering must still be judged valid, and an invalid
        one invalid (so the check is real, not vacuous)."""
        permtab, peritab = hexagon_graph.order()
        dtype = lib.get_scotch_dtype()
        perm_view = np.repeat(permtab.astype(dtype), 2)[::2]
        peri_view = np.repeat(peritab.astype(dtype), 2)[::2]
        assert hexagon_graph.order_check(perm_view, peri_view) is True
        assert (
            hexagon_graph.order_check(
                permtab.astype(wrong_dtype()), peritab.astype(wrong_dtype())
            )
            is True
        )

        # A strided view that is NOT a permutation (duplicate index) must be
        # rejected: proves the compacted copy carries the view's values, not
        # the interleaved memory behind it
        duplicated = peri_view.copy()
        duplicated[1] = duplicated[0]
        assert hexagon_graph.order_check(perm_view, duplicated) is False
        wide_duplicated = np.repeat(duplicated, 2)[::2]
        assert hexagon_graph.order_check(perm_view, wide_duplicated) is False

    def test_order_check_only_inspects_peritab(self, hexagon_graph):
        """Pins an upstream limitation: SCOTCH_graphOrderCheck (order_check.c,
        7.0.13) validates peritab as a permutation and the column-block tree,
        but never compares permtab against it. A permtab that is NOT the
        inverse of peritab therefore passes. Documented in
        docs/QUESTIONS_FOR_SCOTCH_TEAM.md; this test fails the day upstream
        tightens the check, so we notice."""
        permtab, peritab = hexagon_graph.order()
        inconsistent = permtab.copy()
        inconsistent[0], inconsistent[1] = inconsistent[1], inconsistent[0]
        assert not np.array_equal(inconsistent, permtab)
        assert hexagon_graph.order_check(inconsistent, peritab) is True

    def test_partition_fixed_from_strided_view(self, grid_4x4_graph):
        """partition_fixed copies the caller's array (copy=True): a strided view
        must be honoured and the caller's view left untouched."""
        dtype = lib.get_scotch_dtype()
        base = np.repeat(np.full(16, -1, dtype=dtype), 2)
        fixed_view = base[::2]
        fixed_view[0] = 0  # pin vertex 0 to part 0
        fixed_view[15] = 1  # pin vertex 15 to part 1
        before = fixed_view.copy()

        parts = grid_4x4_graph.partition_fixed(2, fixed_view)
        assert parts[0] == 0 and parts[15] == 1
        assert set(np.unique(parts)) <= {0, 1}
        np.testing.assert_array_equal(fixed_view, before)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
