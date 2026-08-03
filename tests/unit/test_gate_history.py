from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.history import validate_weight_vector, weighted_index


def test_weighted_index_uses_half_open_cumulative_ranges() -> None:
    weights = (2, 1, 0, 0, 0, 1)
    assert [weighted_index(weights, roll) for roll in range(4)] == [0, 0, 1, 5]


@pytest.mark.parametrize(
    ("weights", "pattern"),
    [
        ((1, 2), "six"),
        ((0, 0, 0, 0, 0, 0), "six zero"),
        ((1, -1, 1, 1, 1, 1), "negative"),
        ((256, 1, 1, 1, 1, 1), "8-bit"),
    ],
)
def test_weight_vector_requires_six_nonzero_unsigned_bytes(
    weights: tuple[int, ...], pattern: str
) -> None:
    with pytest.raises(WorkspaceError, match=pattern):
        validate_weight_vector(weights)


def test_roll_must_be_inside_total() -> None:
    with pytest.raises(WorkspaceError, match=r"\[0, 6\)"):
        weighted_index((1, 1, 1, 1, 1, 1), 6)


def test_weighted_index_rejects_boolean_roll() -> None:
    with pytest.raises(WorkspaceError, match="integer"):
        weighted_index((1, 1, 1, 1, 1, 1), True)
