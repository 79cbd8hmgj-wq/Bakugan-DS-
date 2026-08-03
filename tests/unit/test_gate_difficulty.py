from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.difficulty import (
    DifficultyEvidence,
    DifficultyValue,
)
from bakugan_ds.gates.model import Confidence


def confirmed_value(value: int, label: str) -> DifficultyValue:
    return DifficultyValue(
        value=value,
        label=label,
        evidence=f"controlled {label} selection",
    )


def complete_difficulty() -> DifficultyEvidence:
    return DifficultyEvidence(
        owner_structure="authoritative battle-setup configuration",
        access="confirmed unsigned byte field",
        width_bits=8,
        values=(
            confirmed_value(0, "easy"),
            confirmed_value(1, "normal"),
            confirmed_value(2, "hard"),
        ),
        initialization="battle setup initializes the selected opponent difficulty",
        profile_change="battle setup selection replaces the prior value",
        battle_load="the same value is copied into live battle AI state",
        ai_consumers=(
            "AI planning consumer A",
            "AI planning consumer B",
        ),
        reset="new battle setup replaces the match-local value",
        confidence=Confidence.CONFIRMED,
        evidence="exact executable and controlled runtime evidence",
    )


def test_difficulty_rejects_duplicate_raw_values() -> None:
    duplicate = (
        confirmed_value(0, "easy"),
        confirmed_value(0, "normal"),
    )
    with pytest.raises(WorkspaceError, match="duplicate difficulty value"):
        replace(complete_difficulty(), values=duplicate).validate()


def test_difficulty_rejects_duplicate_labels() -> None:
    duplicate = (
        confirmed_value(0, "easy"),
        confirmed_value(1, "easy"),
    )
    with pytest.raises(WorkspaceError, match="duplicate difficulty label"):
        replace(complete_difficulty(), values=duplicate).validate()


def test_difficulty_requires_battle_load_evidence() -> None:
    with pytest.raises(WorkspaceError, match="battle load"):
        replace(complete_difficulty(), battle_load="").validate()


def test_difficulty_requires_ai_consumers() -> None:
    with pytest.raises(WorkspaceError, match="AI consumers"):
        replace(complete_difficulty(), ai_consumers=()).validate()


def test_difficulty_requires_confirmed_evidence() -> None:
    with pytest.raises(WorkspaceError, match="must be confirmed"):
        replace(
            complete_difficulty(),
            confidence=Confidence.PROBABLE,
        ).validate()


def test_difficulty_values_must_fit_declared_width() -> None:
    with pytest.raises(WorkspaceError, match="does not fit"):
        replace(
            complete_difficulty(),
            values=(
                confirmed_value(0, "easy"),
                confirmed_value(256, "invalid"),
            ),
        ).validate()


def test_complete_difficulty_evidence_validates() -> None:
    complete_difficulty().validate()
