from __future__ import annotations

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from bakugan_ds.compression.blz import decompress_blz
from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.authoring import (
    approved_juggernoid_record,
    legacy_passthrough_record,
    load_authoring_document,
)
from bakugan_ds.gates.install import (
    ARENA_LOW_EXPECTED,
    ARENA_LOW_OFFSET,
    ARENA_LOW_REPLACEMENT,
    install_milestone_6c,
)
from bakugan_ds.gates.loader import (
    CACHE_SIZE,
    parse_cache,
)
from bakugan_ds.gates.record import (
    G2DT_HEADER_SIZE,
    GATE_RECORD_SIZE,
    TRAILER_SIZE,
    build_trailer,
    parse_trailer,
    serialize_record,
)
from bakugan_ds.gates.runtime_module import build_milestone_6c_module
from bakugan_ds.gates.system2 import (
    FallbackReason,
    FallbackScope,
    GateCalculationContext,
    calculate_gate_bonus,
    compress_core_g_for_gate,
)
from bakugan_ds.inspection import inspect_rom
from bakugan_ds.patches.apply import apply_patch_set
from bakugan_ds.profile import RomProfile
from bakugan_ds.workspace.manifest import WorkspaceManifest, sha256_bytes
from bakugan_ds.workspace.rebuild import RebuildOptions, rebuild_rom

AUTHORING = Path("config/gates/milestone-6c-system2-v1.json")
CORE_PATCH = Path("patches/core-g-compression-400.json")
SOURCE_ROM_SHA256 = "7b8f0ac330d3bf7cef2acb8e4e9318e797e1f2e051f1c2f1c87d998ef8d2558b"
REBUILT_ROM_SHA256 = "d353b38f83d7c6790fefbcb50fb2583fa92f9a53d9601038f8743b3b730f1a41"
BUILD_REPORT_SHA256 = "b12900aadfc38a4499b455247fe42415ab8a84cbba2e48f6bd0ad67d821cc97f"
TRAILER_SHA256 = "c67d3bad47ad318ea782a938fc3412a6244509e96b0d2fb75e3bf8424c9fe72b"
MODULE_SHA256 = "cb0d3734ba0dfba383313890c787f7307eacfa2da0f14d45396f06e090adc178"
RAW_CARRIER_SHA256 = "6961673e91f0ced7afa299d371ba54d73b3e64ab75c79e14224e59c56003b634"
OVERLAY_SHA256 = "78d8e5963673c77a14fb36548b269fb8ab9abca9968b40167494531196b11b96"
STORED_ARM9_SHA256 = "95494b52cb94c85f7209ddf00fd37b6289fdecd6ad855f7344132b3f840236f8"


def _payload(data: bytes, inspection, file_id: int) -> bytes:
    entry = inspection.fat[file_id]
    return data[entry.start : entry.end]


def _install_workspace(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination, copy_function=shutil.copyfile)
    apply_patch_set(destination, CORE_PATCH)
    install_milestone_6c(destination, AUTHORING)
    return destination


@pytest.mark.integration
def test_exact_milestone_6c_build_is_deterministic_and_bounded(
    reference_rom: Path,
    reference_profile: RomProfile,
    reference_workspace: tuple[Path, WorkspaceManifest],
    tmp_path: Path,
) -> None:
    source_workspace, _manifest = reference_workspace
    workspace = _install_workspace(source_workspace, tmp_path / "workspace")
    first = tmp_path / "milestone-6c-a.nds"
    second = tmp_path / "milestone-6c-b.nds"
    first_report = rebuild_rom(
        reference_rom,
        reference_profile,
        workspace,
        RebuildOptions(first),
    )
    second_report = rebuild_rom(
        reference_rom,
        reference_profile,
        workspace,
        RebuildOptions(second),
    )

    source = reference_rom.read_bytes()
    first_data = first.read_bytes()
    second_data = second.read_bytes()
    assert sha256_bytes(source) == SOURCE_ROM_SHA256
    assert len(first_data) == len(second_data) == len(source) == 134_217_728
    assert first_data == second_data
    assert first_report.output_sha256 == second_report.output_sha256 == REBUILT_ROM_SHA256
    assert (
        first.with_suffix(".nds.build.json").read_bytes()
        == second.with_suffix(".nds.build.json").read_bytes()
    )
    assert sha256_bytes(first.with_suffix(".nds.build.json").read_bytes()) == (BUILD_REPORT_SHA256)
    assert [(item.kind, item.identifier, item.encoding) for item in first_report.changes] == [
        ("arm9", "arm9", "raw"),
        ("nitrofs_raw", "font/mes_CardName.mes", "raw-override"),
        ("overlay", "7", "uncompressed-overlay"),
    ]

    original = inspect_rom(reference_rom, reference_profile, require_supported=True)
    rebuilt = inspect_rom(first, reference_profile, require_supported=False)
    assert rebuilt.layout_mismatches == ()
    assert len(rebuilt.fat) == len(original.fat) == 11_005
    assert len(rebuilt.fnt.files) == len(original.fnt.files) == 10_996
    assert [(item.file_id, item.path) for item in rebuilt.fnt.files] == [
        (item.file_id, item.path) for item in original.fnt.files
    ]
    assert len(rebuilt.arm9_overlays) == len(original.arm9_overlays) == 9

    changed_ids = {7, 2762}
    for original_entry, rebuilt_entry in zip(original.fat, rebuilt.fat, strict=True):
        assert original_entry.file_id == rebuilt_entry.file_id
        if original_entry.file_id in changed_ids:
            continue
        assert (
            source[original_entry.start : original_entry.end]
            == first_data[rebuilt_entry.start : rebuilt_entry.end]
        )

    carrier = _payload(first_data, rebuilt, 2762)
    assert len(carrier) == 2840 + TRAILER_SIZE == 6992
    assert sha256_bytes(carrier) == RAW_CARRIER_SHA256
    trailer = carrier[-TRAILER_SIZE:]
    assert sha256_bytes(trailer) == TRAILER_SHA256
    header, records = parse_trailer(trailer)
    assert header.header_size == G2DT_HEADER_SIZE
    assert header.record_size == GATE_RECORD_SIZE
    assert len(records) == 103
    assert records[18] == approved_juggernoid_record()
    assert records[19] == legacy_passthrough_record(20)
    assert records[21] == legacy_passthrough_record(22)

    overlay_entry = next(item for item in rebuilt.arm9_overlays if item.overlay_id == 7)
    assert overlay_entry.ram_size == 0x7A7E0
    assert overlay_entry.bss_size == 0x40
    assert overlay_entry.flags == 0
    assert overlay_entry.compressed_size == 0
    overlay = _payload(first_data, rebuilt, overlay_entry.file_id)
    assert len(overlay) == 0x7A7E0
    assert sha256_bytes(overlay) == OVERLAY_SHA256
    assert overlay[0x721A0:0x727E0] == b"\0" * 0x640

    module = build_milestone_6c_module()
    assert len(module.image) == 0x8000
    assert sha256_bytes(module.image) == MODULE_SHA256
    assert overlay[0x727E0:0x7A7E0] == module.image
    for hook in module.hook_replacements:
        assert (
            overlay[hook.component_offset : hook.component_offset + len(hook.replacement)]
            == hook.replacement
        )

    core_patch = json.loads(CORE_PATCH.read_text(encoding="utf-8"))
    for patch in core_patch["patches"]:
        offset = patch["offset"]
        replacement = bytes.fromhex(patch["replacement"])
        assert overlay[offset : offset + len(replacement)] == replacement

    original_arm9 = source[
        original.header.arm9_offset : original.header.arm9_offset + original.header.arm9_size
    ]
    rebuilt_arm9 = first_data[
        rebuilt.header.arm9_offset : rebuilt.header.arm9_offset + rebuilt.header.arm9_size
    ]
    assert len(rebuilt_arm9) == len(original_arm9) == 448_192
    assert sha256_bytes(rebuilt_arm9) == STORED_ARM9_SHA256
    original_decoded = decompress_blz(original_arm9)
    rebuilt_decoded = decompress_blz(rebuilt_arm9)
    assert len(rebuilt_decoded) == len(original_decoded) == 786_712
    assert original_decoded[ARENA_LOW_OFFSET : ARENA_LOW_OFFSET + 4] == ARENA_LOW_EXPECTED
    assert rebuilt_decoded[ARENA_LOW_OFFSET : ARENA_LOW_OFFSET + 4] == (ARENA_LOW_REPLACEMENT)
    assert original_decoded[:ARENA_LOW_OFFSET] == rebuilt_decoded[:ARENA_LOW_OFFSET]
    assert original_decoded[ARENA_LOW_OFFSET + 4 :] == rebuilt_decoded[ARENA_LOW_OFFSET + 4 :]


def test_malformed_system2_inputs_predict_fail_closed_legacy_behavior() -> None:
    records = load_authoring_document(AUTHORING)
    trailer = bytearray(build_trailer(records))

    corrupt_magic = bytearray(trailer)
    corrupt_magic[0] ^= 0x01
    with pytest.raises(WorkspaceError, match="magic"):
        parse_trailer(bytes(corrupt_magic))

    corrupt_crc = bytearray(trailer)
    corrupt_crc[24] ^= 0x01
    with pytest.raises(WorkspaceError, match="CRC"):
        parse_trailer(bytes(corrupt_crc))

    cache = bytearray(CACHE_SIZE)
    cache[:GATE_RECORD_SIZE] = serialize_record(approved_juggernoid_record())
    cache[0x28] = 20
    cache[0x29] = 1
    cache[0x2A] = 1
    cache[0x2B] = 0
    assert parse_cache(bytes(cache)) is None

    cache[0x28] = 19
    cache[0x3C] = 1
    assert parse_cache(bytes(cache)) is None

    context = GateCalculationContext(190, 1, 0, 0, 0, 1, 19)
    invalid_enum = replace(approved_juggernoid_record(), archetype=2)
    result = calculate_gate_bonus(invalid_enum, context)
    assert result.effective_gate_bonus is None
    assert result.target_total_g is None
    assert result.fallback_scope is FallbackScope.RECORD
    assert result.fallback_reason is FallbackReason.INVALID_ENUM

    invalid_values = replace(approved_juggernoid_record(), activation_limit=1)
    result = calculate_gate_bonus(invalid_values, context)
    assert result.effective_gate_bonus is None
    assert result.target_total_g is None
    assert result.fallback_scope is FallbackScope.RECORD
    assert result.fallback_reason is FallbackReason.UNSUPPORTED_RECORD


def test_legacy_gate_samples_preserve_all_bonus_values_and_fixed_scratch_type() -> None:
    identity = json.loads(Path("analysis/gates/card-id-evidence.json").read_text())
    rows = {item["card_id"]: item for item in identity["selected_rows"]}
    assert rows[20]["raw_values"] == [16, 11, 9, 12, 9, 4]
    assert rows[20]["bonuses_g"] == [160, 110, 90, 120, 90, 40]
    assert rows[22]["raw_values"] == [18, 6, 9, 14, 13, 5]
    assert rows[22]["bonuses_g"] == [180, 60, 90, 140, 130, 50]

    records = load_authoring_document(AUTHORING)
    for card_id in (20, 22):
        record = records[card_id - 1]
        assert record == legacy_passthrough_record(card_id)
        for attribute_id in range(6):
            context = GateCalculationContext(
                compressed_core_g=190,
                attribute_id=attribute_id,
                current_participant=0,
                owner_participant=0,
                owner_side_score=0,
                opposing_side_score=0,
                gate_id=card_id,
            )
            result = calculate_gate_bonus(record, context)
            assert result.effective_gate_bonus is None
            assert result.target_total_g is None
            assert result.fallback_scope is FallbackScope.RECORD
            assert result.fallback_reason is FallbackReason.LEGACY_PASSTHROUGH

    value = os.environ.get("BAKUGAN_DS_RUNTIME_ARM9")
    if value is None:
        pytest.skip("set BAKUGAN_DS_RUNTIME_ARM9 to verify exact Gate metadata")
    arm9 = Path(value)
    if not arm9.is_file():
        pytest.fail(f"BAKUGAN_DS_RUNTIME_ARM9 does not point to a file: {arm9}")
    data = arm9.read_bytes()
    metadata_base = 0xA1258
    for card_id in (20, 22):
        record = data[metadata_base + card_id * 4 : metadata_base + card_id * 4 + 4]
        assert tuple(record) == (0, 0, 0, 1)
        assert record[2] == 0


def test_core_g_reference_curve_remains_compatible_with_system2() -> None:
    assert {
        value: compress_core_g_for_gate(value)
        for value in (190, 400, 401, 410, 440, 500, 650, 900, 990)
    } == {
        190: 190,
        400: 400,
        401: 400,
        410: 405,
        440: 420,
        500: 450,
        650: 525,
        900: 650,
        990: 695,
    }
