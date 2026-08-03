from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.selector import resolve_battle_type_precedence


def test_explicit_constructor_type_bypasses_fallback() -> None:
    assert resolve_battle_type_precedence(3, 1, None) == 3


def test_negative_one_constructor_type_uses_fallback() -> None:
    assert resolve_battle_type_precedence(-1, 1, None) == 1


def test_scripted_override_supersedes_provisional_type() -> None:
    assert resolve_battle_type_precedence(3, 1, 5) == 5


def test_selector_precedence_rejects_out_of_range_type() -> None:
    with pytest.raises(WorkspaceError, match="constructor type"):
        resolve_battle_type_precedence(6, 1, None)
