from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.loader import (
    ARM9_DECODED_SHA256,
    CACHE_ADDRESS,
    FS_FILE_SIZE,
    GATE_CLEAR_HOOK_ADDRESS,
    GATE_CLEAR_RETURN_ADDRESS,
    GATE_LOADER_HOOK_ADDRESS,
    GATE_LOADER_RETURN_ADDRESS,
    INITIALIZED_CACHE_SHA256,
    INSTRUMENTED_ROM_SHA256,
    INVALIDATED_CACHE_SHA256,
    ROM_ARCHIVE_ADDRESS,
    SYSTEM2_RUNTIME_MODULE_SHA256,
    CacheLayout,
    append_validated_trailer,
    build_cache,
    build_expanded_overlay,
    invalidate_cache,
    load_trailer_or_none,
    parse_cache,
    reference_loader_evidence,
    validate_overlay_expansion,
)
from bakugan_ds.gates.record import GateRecordV1, build_trailer


def record(card_id: int) -> GateRecordV1:
    return GateRecordV1(
        card_id=card_id,
        archetype=0,
        flags=0,
        flat_bonus_g=0,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        battle_weights=(0, 0, 0, 0, 0, 0),
        preferred_type=255,
        condition_id=0,
        effect_id=0,
        drawback_id=0,
        effect_value=0,
        drawback_value=0,
        activation_limit=0,
        fatigue_rate=0,
        target_mode=0,
        timing_phase=0,
        condition_value=0,
        secondary_effect_id=0,
        secondary_condition_id=0,
        secondary_value=0,
        reserved=0,
    )


def roster() -> tuple[GateRecordV1, ...]:
    return tuple(record(card_id) for card_id in range(1, 104))


def synthetic_lz10() -> bytes:
    return b"\x10\x01\x00\x00\x00A"


def test_expanded_overlay_preserves_original_bss_addresses() -> None:
    original = b"A" * 0x721A0
    module = b"B" * 0x8000
    expanded = build_expanded_overlay(original, module)
    assert len(expanded) == 0x7A7E0
    assert expanded[0x721A0:0x727E0] == b"\0" * 0x640
    assert expanded[0x727E0:0x7A7E0] == module
    validate_overlay_expansion(
        original,
        expanded,
        CacheLayout(),
        expected_original_sha256=None,
    )


def test_overlay_expansion_rejects_nonzero_preserved_bss() -> None:
    original = b"A" * 0x721A0
    expanded = bytearray(build_expanded_overlay(original, b"B" * 0x8000))
    expanded[0x721A0] = 1
    with pytest.raises(WorkspaceError, match="preserved BSS"):
        validate_overlay_expansion(
            original,
            bytes(expanded),
            CacheLayout(),
            expected_original_sha256=None,
        )


def test_validated_trailer_round_trip_and_legacy_fallback() -> None:
    carrier = synthetic_lz10()
    trailer = build_trailer(roster())
    combined = append_validated_trailer(
        carrier,
        trailer,
        expected_raw_sha256=None,
    )
    loaded = load_trailer_or_none(combined, raw_size=len(carrier))
    assert loaded is not None
    assert loaded[0].card_id == 1

    corrupted = bytearray(combined)
    corrupted[-1] ^= 1
    assert load_trailer_or_none(bytes(corrupted), raw_size=len(carrier)) is None
    assert load_trailer_or_none(carrier, raw_size=len(carrier)) is None
    assert load_trailer_or_none(combined[:-1], raw_size=len(carrier)) is None


def test_validated_trailer_rejects_existing_trailer() -> None:
    trailer = build_trailer(roster())
    combined = append_validated_trailer(
        synthetic_lz10(),
        trailer,
        expected_raw_sha256=None,
    )
    with pytest.raises(WorkspaceError, match="already contains"):
        append_validated_trailer(
            combined,
            trailer,
            expected_raw_sha256=None,
        )


def test_cache_build_parse_and_invalidate() -> None:
    cache = build_cache(record(21), arena_entry=3)
    assert len(cache) == 0x40
    assert cache[0x28:0x2C] == bytes((21, 1, 1, 3))
    assert parse_cache(cache) == record(21)
    invalidated = invalidate_cache(cache)
    assert invalidated == b"\0" * 0x40
    assert parse_cache(invalidated) is None


def test_cache_rejects_invalid_arena_entry_and_mismatched_id() -> None:
    with pytest.raises(WorkspaceError, match="arena entry"):
        build_cache(record(1), arena_entry=12)
    cache = bytearray(build_cache(record(1), arena_entry=0))
    cache[0x28] = 2
    assert parse_cache(bytes(cache)) is None


def test_cache_layout_is_contiguous_and_below_arena() -> None:
    layout = CacheLayout()
    layout.validate()
    assert layout.module_start == 0x0228BC20
    assert layout.module_start + layout.module_size == layout.cache_start
    assert layout.cache_start == CACHE_ADDRESS
    assert layout.cache_start + layout.cache_size == layout.arena_low
    assert layout.arena_low < layout.arena_high


def test_reference_loader_evidence_matches_confirmed_runtime_trace() -> None:
    evidence = reference_loader_evidence()
    evidence.validate()
    assert ARM9_DECODED_SHA256 == (
        "7cc01c584d2ecdd7166471f218f9fc3a58cf102b5fbe925287b9b95bae0c221e"
    )
    assert FS_FILE_SIZE == 72
    assert ROM_ARCHIVE_ADDRESS == 0x020BFCB4
    assert evidence.open_op.function == 0x0200AA24
    assert evidence.read_op.function == 0x0200AC30
    assert evidence.seek_op.function == 0x0200AC40
    assert evidence.close_op.function == 0x0200AADC
    assert evidence.stack_read_size == FS_FILE_SIZE
    assert evidence.open_op.confidence == "confirmed"
    assert evidence.read_op.confidence == "confirmed"
    assert evidence.seek_op.confidence == "confirmed"
    assert evidence.close_op.confidence == "confirmed"
    assert "88040" in evidence.read_op.evidence
    assert "0x0223D1D0" in evidence.initialization
    assert "Gate ID 21" in evidence.initialization
    assert "0x022424B8" in evidence.invalidation
    assert "all 64 cache bytes zero" in evidence.invalidation


def test_runtime_cache_lifecycle_constants_are_exact() -> None:
    assert CACHE_ADDRESS == 0x02293C20
    assert GATE_LOADER_HOOK_ADDRESS == 0x0223D1CC
    assert GATE_LOADER_RETURN_ADDRESS == 0x0223D1D0
    assert GATE_CLEAR_HOOK_ADDRESS == 0x022424B4
    assert GATE_CLEAR_RETURN_ADDRESS == 0x022424B8
    assert INSTRUMENTED_ROM_SHA256 == (
        "8177aff2ca1c6cfe401c4401ccfca954e17d1d546612628d0bc6e032b2d15388"
    )
    assert SYSTEM2_RUNTIME_MODULE_SHA256 == (
        "d18dd0f7eba1279295e2314fa2d125030f0d382e577fad2fd9d712a623202ca6"
    )
    assert INITIALIZED_CACHE_SHA256 == (
        "8ecef0a63d0ba161fe000ab688d847fe774bbbd4a5da412d281eb68d9d1b657d"
    )
    assert INVALIDATED_CACHE_SHA256 == (
        "f5a5fd42d16a20302798ef6ed309979b43003d2320d9f0e8ea9831a92759fb4b"
    )
