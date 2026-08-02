from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.match_state import (
    CounterEvidence,
    CounterOwner,
    MatchStateEvidence,
    normalize_match_state_artifact,
)
from bakugan_ds.gates.model import Confidence


def confirmed_counter(
    name: str, owner: CounterOwner, *, access: str
) -> CounterEvidence:
    return CounterEvidence(
        name=name,
        owner=owner,
        width_bits=8,
        access=access,
        initial_value=0,
        update_function="confirmed gameplay update function",
        reset_function="participant constructor",
        lifetime="participant object / match session",
        confidence=Confidence.CONFIRMED,
        evidence="runtime and exact-binary evidence",
    )


def confirmed_model() -> MatchStateEvidence:
    return MatchStateEvidence(
        score_counters=(
            confirmed_counter("player_score", CounterOwner.PLAYER, access="+0xEE"),
            confirmed_counter(
                "opponent_score", CounterOwner.OPPONENT, access="+0xEE"
            ),
        ),
        capture_counters=(
            confirmed_counter(
                "player_capture_history_count", CounterOwner.PLAYER, access="+0xF4"
            ),
            confirmed_counter(
                "opponent_capture_history_count",
                CounterOwner.OPPONENT,
                access="+0xF4",
            ),
        ),
        victory_threshold=3,
        result_timing="score store precedes capture-history append and victory check",
        scripted_paths=(
            "normal result",
            "specialized result",
            "scripted score seeding",
        ),
    )


def payload() -> dict[str, object]:
    model = confirmed_model()

    def item(counter: CounterEvidence) -> dict[str, object]:
        return {
            "access": counter.access,
            "confidence": counter.confidence.value,
            "evidence": counter.evidence,
            "initial_value": counter.initial_value,
            "lifetime": counter.lifetime,
            "name": counter.name,
            "owner": counter.owner.value,
            "reset_function": counter.reset_function,
            "update_function": counter.update_function,
            "width_bits": counter.width_bits,
        }

    return {
        "capture_counters": [item(value) for value in model.capture_counters],
        "format_version": 1,
        "profile_id": "b6re_rev0",
        "result_timing": model.result_timing,
        "score_counters": [item(value) for value in model.score_counters],
        "scripted_paths": list(model.scripted_paths),
        "victory_threshold": model.victory_threshold,
    }


def test_match_state_requires_two_participant_counter_pairs() -> None:
    model = confirmed_model()

    model.validate()
    assert model.score_for(CounterOwner.PLAYER).access == "+0xEE"
    assert model.capture_for(CounterOwner.OPPONENT).access == "+0xF4"


def test_match_state_rejects_presentation_only_counter() -> None:
    counter = confirmed_counter("player_score", CounterOwner.PLAYER, access="+0xEE")
    counter = replace(counter, update_function="", evidence="UI draw only")

    with pytest.raises(WorkspaceError, match="update function"):
        counter.validate()


def test_match_state_rejects_missing_opponent_score() -> None:
    model = confirmed_model()
    duplicate_player = replace(
        model.score_counters[1], owner=CounterOwner.PLAYER
    )

    with pytest.raises(WorkspaceError, match="duplicate score counter owner"):
        replace(
            model, score_counters=(model.score_counters[0], duplicate_player)
        ).validate()


def test_match_state_rejects_shared_counter_in_participant_pair() -> None:
    model = confirmed_model()
    shared = replace(model.capture_counters[1], owner=CounterOwner.SHARED)

    with pytest.raises(WorkspaceError, match="player and opponent owners"):
        replace(model, capture_counters=(model.capture_counters[0], shared)).validate()


def test_match_state_rejects_probable_counter() -> None:
    counter = replace(
        confirmed_model().score_counters[0], confidence=Confidence.PROBABLE
    )

    with pytest.raises(WorkspaceError, match="must be confirmed"):
        counter.validate()


def test_match_state_rejects_nonpositive_or_out_of_width_threshold() -> None:
    model = confirmed_model()

    with pytest.raises(WorkspaceError, match="must be positive"):
        replace(model, victory_threshold=0).validate()
    with pytest.raises(WorkspaceError, match="does not fit"):
        replace(model, victory_threshold=256).validate()


def test_normalize_match_state_artifact_accepts_dual_schema_payload() -> None:
    data = payload()
    data["domain"] = "match-score-and-capture"
    data["fields"] = []
    model = normalize_match_state_artifact(data)

    assert model.victory_threshold == 3
    assert model.score_for(CounterOwner.OPPONENT).name == "opponent_score"


def test_normalize_match_state_artifact_rejects_boolean_width() -> None:
    data = payload()
    counters = list(cast(list[object], data["score_counters"]))
    first = dict(cast(dict[str, object], counters[0]))
    first["width_bits"] = True
    counters[0] = first
    data["score_counters"] = counters

    with pytest.raises(WorkspaceError, match="must be an integer"):
        normalize_match_state_artifact(data)
