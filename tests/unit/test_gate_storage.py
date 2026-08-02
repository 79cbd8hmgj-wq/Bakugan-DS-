from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.storage import (
    StorageCandidate,
    StorageDecision,
    validate_storage_decision,
)


def candidate(name: str, *, viable: bool, unresolved: tuple[str, ...] = ()) -> StorageCandidate:
    return StorageCandidate(
        name=name,
        scope="full_roster" if name == "hybrid" else "milestone_6b_prototype",
        confirmed_requirements=("confirmed requirement",),
        unresolved_requirements=unresolved,
        risks=("bounded risk",),
        viable=viable,
    )


def test_storage_decision_requires_distinct_viable_primary_and_fallback() -> None:
    decision = StorageDecision(
        primary="hybrid",
        fallback="hybrid",
        candidates=(candidate("hybrid", viable=True),),
        evidence=("evidence",),
    )
    with pytest.raises(WorkspaceError, match="distinct"):
        validate_storage_decision(decision)


def test_viable_candidate_cannot_have_unresolved_requirements() -> None:
    decision = StorageDecision(
        primary="hybrid",
        fallback="expanded_executable_overlay",
        candidates=(
            candidate("hybrid", viable=True, unresolved=("heap safety",)),
            candidate("expanded_executable_overlay", viable=True),
            candidate("nitrofs", viable=False, unresolved=("new FNT entry",)),
            candidate("dedicated_overlay", viable=False, unresolved=("overlay loader",)),
        ),
        evidence=("evidence",),
    )
    with pytest.raises(WorkspaceError, match="unresolved"):
        validate_storage_decision(decision)


def test_storage_decision_requires_all_four_candidate_categories() -> None:
    decision = StorageDecision(
        primary="hybrid",
        fallback="expanded_executable_overlay",
        candidates=(
            candidate("hybrid", viable=True),
            candidate("expanded_executable_overlay", viable=True),
        ),
        evidence=("evidence",),
    )
    with pytest.raises(WorkspaceError, match="missing storage candidates"):
        validate_storage_decision(decision)


def test_confirmed_storage_decision_is_valid() -> None:
    decision = StorageDecision(
        primary="hybrid",
        fallback="expanded_executable_overlay",
        candidates=(
            candidate("nitrofs", viable=False, unresolved=("new FNT entry",)),
            candidate("expanded_executable_overlay", viable=True),
            candidate("dedicated_overlay", viable=False, unresolved=("load coordination",)),
            candidate("hybrid", viable=True),
        ),
        evidence=("arena low boundary confirmed", "trailer size bounded"),
    )
    validate_storage_decision(decision)


def test_raw_lz10_trailer_does_not_change_native_decoded_payload() -> None:
    from bakugan_ds.compression.lz10 import decompress_lz10
    from bakugan_ds.gates.storage import append_lz10_trailer, extract_lz10_trailer

    raw = bytes([0x10, 0x03, 0x00, 0x00, 0x00]) + b"abc"
    trailer = b"G2DT" + b"x" * 28
    combined = append_lz10_trailer(raw, trailer, maximum_size=64)

    assert decompress_lz10(combined) == b"abc"
    assert extract_lz10_trailer(combined, len(trailer), b"G2DT") == trailer


def test_trailer_rejects_bad_magic_and_oversize() -> None:
    from bakugan_ds.gates.storage import append_lz10_trailer, extract_lz10_trailer

    raw = bytes([0x10, 0x01, 0x00, 0x00, 0x00, ord("a")])
    with pytest.raises(WorkspaceError, match="maximum"):
        append_lz10_trailer(raw, b"G2DT" + b"x" * 20, maximum_size=8)
    with pytest.raises(WorkspaceError, match="magic"):
        extract_lz10_trailer(raw + b"BAD!" + b"x" * 4, 8, b"G2DT")


def test_approved_system2_storage_decision_is_valid() -> None:
    from bakugan_ds.gates.storage import SYSTEM2_STORAGE_DECISION

    validate_storage_decision(SYSTEM2_STORAGE_DECISION)
    assert SYSTEM2_STORAGE_DECISION.primary == "hybrid"
    assert SYSTEM2_STORAGE_DECISION.fallback == "nitrofs"
