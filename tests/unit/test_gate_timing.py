from __future__ import annotations

from dataclasses import replace

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence
from bakugan_ds.gates.timing import (
    EffectPhase,
    TimingBoundaryEvidence,
    TimingModel,
)

BASE = 0x02219440


def boundary(phase: EffectPhase, index: int) -> TimingBoundaryEvidence:
    address = BASE + 0x100 + index * 4
    return TimingBoundaryEvidence(
        phase=phase,
        component="overlay_0007",
        address=address,
        component_offset=address - BASE,
        live_registers=("pc and owner register captured",),
        owner_objects=("live owner object",),
        valid_fields=("confirmed field",),
        mutations_allowed="battle-local mutation only",
        scripted_bypass="scripted behavior is documented",
        rollback="legacy behavior is preserved",
        confidence=Confidence.CONFIRMED,
        evidence="exact binary and controlled runtime evidence",
    )


def complete_model() -> TimingModel:
    return TimingModel(
        boundaries=tuple(
            boundary(phase, index)
            for index, phase in enumerate(EffectPhase)
        )
    )


def test_timing_requires_every_phase_exactly_once() -> None:
    model = complete_model()
    model.validate()
    with pytest.raises(WorkspaceError, match="missing phases"):
        TimingModel(boundaries=model.boundaries[:-1]).validate()


def test_timing_rejects_duplicate_phase() -> None:
    model = complete_model()
    duplicate = replace(model.boundaries[-1], phase=EffectPhase.PRE_GATE)
    with pytest.raises(WorkspaceError, match="duplicate effect timing phase"):
        TimingModel(boundaries=model.boundaries[:-1] + (duplicate,)).validate()


def test_timing_requires_component_relative_address_consistency() -> None:
    item = replace(boundary(EffectPhase.PRE_GATE, 0), component_offset=0)
    with pytest.raises(WorkspaceError, match="inconsistent"):
        item.validate()


def test_timing_requires_valid_fields() -> None:
    item = replace(boundary(EffectPhase.PRE_GATE, 0), valid_fields=())
    with pytest.raises(WorkspaceError, match="valid fields"):
        item.validate()


def test_timing_requires_mutation_policy() -> None:
    item = replace(boundary(EffectPhase.PRE_GATE, 0), mutations_allowed="")
    with pytest.raises(WorkspaceError, match="mutation policy"):
        item.validate()


def test_timing_requires_scripted_behavior_and_rollback() -> None:
    with pytest.raises(WorkspaceError, match="scripted bypass"):
        replace(boundary(EffectPhase.PRE_GATE, 0), scripted_bypass="").validate()
    with pytest.raises(WorkspaceError, match="rollback"):
        replace(boundary(EffectPhase.PRE_GATE, 0), rollback="").validate()


def test_timing_requires_confirmed_evidence() -> None:
    item = replace(
        boundary(EffectPhase.PRE_GATE, 0),
        confidence=Confidence.PROBABLE,
    )
    with pytest.raises(WorkspaceError, match="must be confirmed"):
        item.validate()


def test_timing_boundary_lookup_returns_exact_phase() -> None:
    model = complete_model()
    model.validate()
    assert model.boundary_for(EffectPhase.GATE_CAPTURE).phase is EffectPhase.GATE_CAPTURE
