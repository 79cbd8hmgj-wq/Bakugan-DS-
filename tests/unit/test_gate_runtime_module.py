from __future__ import annotations

import hashlib
import itertools
import json
import struct
from pathlib import Path

import pytest

from bakugan_ds.gates.arm32 import decode_branch_target
from bakugan_ds.gates.hooks import CORE_G_PROTECTED_RANGES
from bakugan_ds.gates.loader import CACHE_ADDRESS, SYSTEM2_MODULE_SIZE
from bakugan_ds.gates.runtime_module import build_milestone_6c_module

MODULE_BASE = 0x0228BC20
MODULE_END = 0x02293C20
CACHE_END = 0x02293C60
CONTRACT = Path("analysis/gates/milestone-6c-runtime-contract.json")

REQUIRED_SYMBOLS = {
    "g2_clear_cache",
    "g2_validate_cache",
    "g2_crc32_update",
    "g2_load_selected_record",
    "g2_validate_selected_record",
    "g2_legacy_gate_bonus",
    "g2_calculate_gate_bonus",
    "g2_gate_bonus_hook",
    "g2_context_store_hook",
    "g2_select_battle_type",
    "g2_selector_hook",
    "g2_loader_trampoline",
    "g2_clear_hook",
    "g2_evaluate_condition",
    "g2_matches_target",
    "g2_apply_effect",
}

EXPECTED_HOOKS = {
    "gate_bonus": (0x0223D258, 0x0223D278, 32),
    "context_access": (0x0223D288, 0x0223D290, 8),
    "battle_type_selector": (0x0223E350, 0x0223E354, 4),
    "expanded_data_lookup": (0x022433AC, 0x022433B0, 4),
    "cache_load": (0x0223D1CC, 0x0223D1D0, 4),
    "cache_clear": (0x022424B4, 0x022424B8, 4),
}


def test_runtime_module_has_fixed_layout_and_symbols() -> None:
    module = build_milestone_6c_module()

    assert len(module.image) == SYSTEM2_MODULE_SIZE == 0x8000
    assert module.symbols["g2_clear_cache"].address == MODULE_BASE
    assert set(module.symbols) == REQUIRED_SYMBOLS
    assert max(symbol.address + symbol.size for symbol in module.symbols.values()) <= MODULE_END
    assert module.sha256 == hashlib.sha256(module.image).hexdigest()


def test_runtime_symbols_do_not_overlap_and_unused_bytes_are_zero() -> None:
    module = build_milestone_6c_module()
    symbols = sorted(module.symbols.values(), key=lambda symbol: symbol.address)

    for left, right in itertools.pairwise(symbols):
        assert left.address + left.size <= right.address

    covered = bytearray(len(module.image))
    for symbol in symbols:
        start = symbol.address - MODULE_BASE
        covered[start : start + symbol.size] = b"\1" * symbol.size
    for index, marker in enumerate(covered):
        if marker == 0:
            assert module.image[index] == 0


def test_all_approved_and_cache_hooks_are_guarded_and_target_symbols() -> None:
    module = build_milestone_6c_module()
    by_name = {hook.name: hook for hook in module.hook_replacements}

    assert set(by_name) == set(EXPECTED_HOOKS)
    for name, (address, return_address, length) in EXPECTED_HOOKS.items():
        hook = by_name[name]
        assert hook.address == address
        assert hook.return_address == return_address
        assert len(hook.expected) == len(hook.replacement) == length
        assert hashlib.sha256(hook.expected).hexdigest() == hook.expected_sha256
        target = decode_branch_target(address, struct.unpack_from("<I", hook.replacement)[0])
        assert target == module.symbols[hook.target_symbol].address
        assert MODULE_BASE <= target < MODULE_END
        assert hook.rollback.strip()


def test_hook_sources_do_not_overlap_core_g_protected_ranges() -> None:
    module = build_milestone_6c_module()

    for hook in module.hook_replacements:
        start = hook.component_offset
        end = start + len(hook.expected)
        for protected in CORE_G_PROTECTED_RANGES:
            assert end <= protected.start or protected.stop <= start


def test_legacy_gate_replay_contains_relocated_lookup_and_exact_return() -> None:
    module = build_milestone_6c_module()
    symbol = module.symbols["g2_legacy_gate_bonus"]
    start = symbol.address - MODULE_BASE
    words = struct.unpack_from(f"<{symbol.size // 4}I", module.image, start)

    assert words[:4] == (
        0xE5D51019,
        0xE1D600B4,
        0xE1A01E01,
        0xE1A01E21,
    )
    assert decode_branch_target(symbol.address + 16, words[4]) == 0x02065BF4
    assert words[5:9] == (
        0xE3A0100A,
        0xE0010190,
        0xE1C511B2,
        0xE3A03000,
    )
    assert decode_branch_target(symbol.address + 36, words[9]) == 0x0223D278


def test_context_and_loader_replay_stubs_preserve_displaced_words() -> None:
    module = build_milestone_6c_module()

    context = module.symbols["g2_context_store_hook"]
    context_words = struct.unpack_from(
        f"<{context.size // 4}I", module.image, context.address - MODULE_BASE
    )
    legacy_pair = (0xE0820001, 0xE1C500BE)
    assert any(
        context_words[index : index + 2] == legacy_pair for index in range(len(context_words) - 1)
    )
    assert context.branch_targets.count(0x0223D290) == 2

    loader = module.symbols["g2_load_selected_record"]
    loader_words = struct.unpack_from(
        f"<{loader.size // 4}I", module.image, loader.address - MODULE_BASE
    )
    assert loader_words[0] == 0xE1C600B4
    assert decode_branch_target(loader.address + 4, loader_words[1]) == (loader.address + 8)

    trampoline = module.symbols["g2_loader_trampoline"]
    trampoline_words = struct.unpack_from(
        f"<{trampoline.size // 4}I",
        module.image,
        trampoline.address - MODULE_BASE,
    )
    assert trampoline_words[0] == 0xE92D4008
    assert 0x022433B0 in trampoline.branch_targets


def test_module_branches_never_target_cache_or_arena_space() -> None:
    module = build_milestone_6c_module()

    for symbol in module.symbols.values():
        assert symbol.code_size <= symbol.size
        for target in symbol.branch_targets:
            assert not (CACHE_ADDRESS <= target < CACHE_END)
            assert target < 0x023E0000


def test_runtime_module_is_deterministic() -> None:
    first = build_milestone_6c_module()
    second = build_milestone_6c_module()

    assert first == second


def test_runtime_contract_documents_abi_and_legacy_only_boundary() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert payload["format_version"] == 1
    assert payload["profile_id"] == "b6re_rev0"
    assert payload["module"] == {
        "base": "0x0228BC20",
        "end": "0x02293C20",
        "size": 32768,
        "cache_start": "0x02293C20",
        "cache_end": "0x02293C60",
    }
    assert payload["task_7_boundary"]["live_system2_behavior"] is False
    assert payload["task_7_boundary"]["all_hooks_route_to_legacy"] is True
    assert payload["abi"]["stack_alignment"] == 8
    assert payload["abi"]["scratch_registers"] == ["r0", "r1", "r2", "r3"]
    assert payload["abi"]["preserved_when_used"] == [
        "r4",
        "r5",
        "r6",
        "r7",
        "r8",
        "r9",
        "r10",
        "r11",
        "lr",
    ]
    assert set(payload["symbols"]).issubset(REQUIRED_SYMBOLS)
    assert {
        "g2_evaluate_condition",
        "g2_matches_target",
        "g2_apply_effect",
    }.isdisjoint(payload["symbols"])


def test_runtime_loader_failure_edges_leave_zero_cache() -> None:
    from bakugan_ds.gates.authoring import load_authoring_document
    from bakugan_ds.gates.loader import RuntimeLoaderFault, simulate_runtime_load
    from bakugan_ds.gates.record import build_trailer

    trailer = build_trailer(
        load_authoring_document(Path("config/gates/milestone-6c-system2-v1.json"))
    )
    carrier = b"\x10" + b"\0" * 2839 + trailer
    for fault in RuntimeLoaderFault:
        if fault is RuntimeLoaderFault.NONE:
            continue
        cache = simulate_runtime_load(carrier, card_id=19, fault=fault)
        assert cache == b"\0" * 64, fault


def test_runtime_loader_accepts_prototype_and_canonical_passthrough() -> None:
    from bakugan_ds.gates.authoring import load_authoring_document
    from bakugan_ds.gates.loader import parse_cache, simulate_runtime_load
    from bakugan_ds.gates.record import build_trailer

    trailer = build_trailer(
        load_authoring_document(Path("config/gates/milestone-6c-system2-v1.json"))
    )
    carrier = b"\x10" + b"\0" * 2839 + trailer

    prototype = parse_cache(simulate_runtime_load(carrier, card_id=19))
    passthrough = parse_cache(simulate_runtime_load(carrier, card_id=21))
    assert prototype is not None and prototype.card_id == 19
    assert passthrough is not None and passthrough.card_id == 21


def _execute_emitted_loader(carrier: bytes, *, card_id: int) -> bytes:
    from bakugan_ds.gates.loader import (
        FS_CLOSE_FILE_ADDRESS,
        FS_INIT_FILE_ADDRESS,
        FS_OPEN_FILE_FAST_ADDRESS,
        FS_READ_FILE_ADDRESS,
        FS_SEEK_FILE_ADDRESS,
    )
    from tests.support.arm32_interpreter import ArmCpu, SparseMemory

    module = build_milestone_6c_module()
    memory = SparseMemory()
    memory.map(MODULE_BASE, module.image)
    memory.map(CACHE_ADDRESS, b"\0" * 64)

    state = {"position": 0, "open": False}

    def return_to_caller(cpu: ArmCpu, value: int) -> None:
        cpu.registers[0] = value & 0xFFFFFFFF
        cpu.registers[15] = cpu.registers[14]

    def init_file(cpu: ArmCpu) -> None:
        return_to_caller(cpu, 1)

    def open_file(cpu: ArmCpu) -> None:
        state["position"] = 0
        state["open"] = True
        return_to_caller(cpu, 1)

    def seek_file(cpu: ArmCpu) -> None:
        if not state["open"] or cpu.registers[2] != 0:
            return_to_caller(cpu, 0)
            return
        offset = cpu.registers[1]
        if offset > len(carrier):
            return_to_caller(cpu, 0)
            return
        state["position"] = offset
        return_to_caller(cpu, 1)

    def read_file(cpu: ArmCpu) -> None:
        if not state["open"]:
            return_to_caller(cpu, 0xFFFFFFFF)
            return
        destination = cpu.registers[1]
        requested = cpu.registers[2]
        start = state["position"]
        chunk = carrier[start : start + requested]
        memory.map(destination, chunk)
        state["position"] = start + len(chunk)
        return_to_caller(cpu, len(chunk))

    def close_file(cpu: ArmCpu) -> None:
        was_open = state["open"]
        state["open"] = False
        return_to_caller(cpu, int(was_open))

    cpu = ArmCpu(
        memory,
        external_calls={
            FS_INIT_FILE_ADDRESS: init_file,
            FS_OPEN_FILE_FAST_ADDRESS: open_file,
            FS_SEEK_FILE_ADDRESS: seek_file,
            FS_READ_FILE_ADDRESS: read_file,
            FS_CLOSE_FILE_ADDRESS: close_file,
        },
    )
    stop = 0x0BADF00C
    cpu.registers[0] = card_id
    cpu.registers[13] = 0x03010000
    cpu.registers[14] = stop
    loader = module.symbols["g2_load_selected_record"]
    cpu.run(loader.address + 8, stop_addresses={stop}, max_steps=1_000_000)
    return bytes(memory.read8(CACHE_ADDRESS + offset) for offset in range(64))


def test_emitted_loader_recomputes_complete_payload_crc() -> None:
    from bakugan_ds.gates.authoring import load_authoring_document
    from bakugan_ds.gates.loader import parse_cache
    from bakugan_ds.gates.record import G2DT_HEADER_SIZE, GATE_RECORD_SIZE, build_trailer

    trailer = build_trailer(
        load_authoring_document(Path("config/gates/milestone-6c-system2-v1.json"))
    )
    carrier = b"\x10" + b"\0" * 2839 + trailer
    valid_cache = _execute_emitted_loader(carrier, card_id=19)
    assert parse_cache(valid_cache) is not None

    corrupted = bytearray(carrier)
    unrelated_record_offset = 2840 + G2DT_HEADER_SIZE + (21 - 1) * GATE_RECORD_SIZE
    corrupted[unrelated_record_offset + 4] ^= 0x01

    assert _execute_emitted_loader(bytes(corrupted), card_id=19) == b"\0" * 64


def test_clear_cache_routine_is_bounded_sixteen_word_loop() -> None:
    module = build_milestone_6c_module()
    symbol = module.symbols["g2_clear_cache"]
    words = struct.unpack_from(f"<{symbol.size // 4}I", module.image, symbol.address - MODULE_BASE)

    assert words[1] == 0xE3A01000
    assert words[2] == 0xE3A02010
    assert words[3] == 0xE4801004
    assert words[4] == 0xE2522001
    assert decode_branch_target(symbol.address + 20, words[5]) == symbol.address + 12
    assert words[6] == 0xE12FFF1E
    assert words[-1] == CACHE_ADDRESS


def test_live_loader_calls_all_confirmed_nitrofs_interfaces() -> None:
    from bakugan_ds.gates.loader import (
        FS_CLOSE_FILE_ADDRESS,
        FS_INIT_FILE_ADDRESS,
        FS_OPEN_FILE_FAST_ADDRESS,
        FS_READ_FILE_ADDRESS,
        FS_SEEK_FILE_ADDRESS,
    )

    module = build_milestone_6c_module()
    symbol = module.symbols["g2_load_selected_record"]
    start = symbol.address - MODULE_BASE
    words = struct.unpack_from(f"<{symbol.size // 4}I", module.image, start)
    targets = {
        decode_branch_target(symbol.address + index * 4, instruction)
        for index, instruction in enumerate(words)
        if (instruction & 0x0F000000) == 0x0B000000
    }

    assert {
        FS_INIT_FILE_ADDRESS,
        FS_OPEN_FILE_FAST_ADDRESS,
        FS_SEEK_FILE_ADDRESS,
        FS_READ_FILE_ADDRESS,
        FS_CLOSE_FILE_ADDRESS,
    } <= targets


def test_live_loader_uses_144_byte_aligned_stack_frame_and_header_constants() -> None:
    module = build_milestone_6c_module()
    symbol = module.symbols["g2_load_selected_record"]
    start = symbol.address - MODULE_BASE
    words = struct.unpack_from(f"<{symbol.size // 4}I", module.image, start)

    assert 0xE24DD090 in words
    assert 0xE28DD090 in words
    assert 0x54443247 in words
    assert 0x00200001 in words
    assert 0x00010028 in words
    assert 0x00000067 in words
    assert 0x00001018 in words
    assert 0x9B7F95AD in words
    assert 0xC58C7E8B in words


def test_loader_trampoline_validates_identity_before_reloading() -> None:
    module = build_milestone_6c_module()
    symbol = module.symbols["g2_loader_trampoline"]
    start = symbol.address - MODULE_BASE
    words = struct.unpack_from(f"<{symbol.size // 4}I", module.image, start)
    branch_targets = [
        decode_branch_target(symbol.address + index * 4, instruction)
        for index, instruction in enumerate(words)
        if (instruction & 0x0E000000) == 0x0A000000
    ]

    assert module.symbols["g2_validate_cache"].address in branch_targets
    assert module.symbols["g2_load_selected_record"].address + 8 in branch_targets
    assert 0x022433B0 in branch_targets


def test_clear_hook_calls_cache_clear_then_replays_original_load() -> None:
    module = build_milestone_6c_module()
    symbol = module.symbols["g2_clear_hook"]
    start = symbol.address - MODULE_BASE
    words = struct.unpack_from(f"<{symbol.size // 4}I", module.image, start)
    targets = [
        decode_branch_target(symbol.address + index * 4, instruction)
        for index, instruction in enumerate(words)
        if (instruction & 0x0E000000) == 0x0A000000
    ]

    assert module.symbols["g2_clear_cache"].address in targets
    assert words[-1] == 0x02241B0C


def test_runtime_contract_documents_task_8_loader_policy() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    boundary = payload["task_8_boundary"]
    assert boundary["live_system2_behavior"] == "loader_and_cache_only"
    assert boundary["gate_calculation"] == "legacy"
    assert boundary["battle_type_selection"] == "legacy_fixed_metadata"
    assert boundary["selected_record_validation"] == (
        "canonical passthrough or exact approved Gate 19 record"
    )
    assert boundary["close_before_cache_valid"] is True
    assert boundary["payload_crc_runtime_policy"] == (
        "recompute IEEE CRC32 across all 103 ordered records and compare it "
        "to the approved header payload CRC32"
    )
    assert boundary["failure_policy"] == "clear all 64 cache bytes"
    assert boundary["approved_header_hex"] == (
        "4732445401002000280001006700000018100000ad957f9b8b7e8cc500000000"
    )


def test_runtime_contract_documents_task_9_live_calculation_policy() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    boundary = payload["task_9_boundary"]
    assert boundary["active_gate_id"] == 19
    assert boundary["live_system2_behavior"] == ("juggernoid_hybrid_gate_calculation")
    assert boundary["calculation"] == (
        "60 + floor(compressed_core_g * 20 / 256) + attribute_modifier"
    )
    assert boundary["attribute_modifier"] == ("Aquos +30 G; all other approved attributes +0 G")
    assert boundary["effect"] == (
        "+40 G only for the Gate owner combatant when owner-side score is lower"
    )
    assert boundary["tie_activates"] is False
    assert boundary["complete_legacy_fallback"] is True
    assert boundary["battle_type_selection"] == ("legacy_fixed_metadata_until_task_10")
    assert boundary["percentage_source"] == ("compressed core G excluding mutable modifier G")
    assert boundary["target_total_clamp"] == ("unsigned_16_on_system2_path_only")
    assert set(boundary["context_sources"]) == {
        "combatant_participant",
        "descriptor_indices",
        "descriptor_participant",
        "gate_owner",
        "match_score",
        "team_flag",
        "teammate",
    }


def _source_core_for_compressed(value: int) -> int:
    if value <= 400:
        return value
    return (value - 200) * 2


def _execute_emitted_gate_case(
    *,
    compressed_core_g: int,
    attribute_id: int,
    owner_score: int,
    opposing_score: int,
    current_participant: int = 0,
    owner_participant: int = 0,
    mutable_modifier_g: int = 0,
    team_scores: tuple[int, int] | None = None,
    descriptor_participant_override: int | None = None,
    ai_owner: bool = False,
    record: object | None = None,
    landing_result: int | None = None,
) -> tuple[int, int, int]:
    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.record import GateRecordV1
    from bakugan_ds.gates.loader import build_cache
    from tests.support.arm32_interpreter import ArmCpu, SparseMemory

    module = build_milestone_6c_module()
    selected_record = approved_juggernoid_record() if record is None else record
    assert isinstance(selected_record, GateRecordV1)
    memory = SparseMemory()
    memory.map(MODULE_BASE, module.image)
    memory.map(CACHE_ADDRESS, build_cache(selected_record, arena_entry=0))

    global_config = 0x020D433C
    session = 0x0229FC80
    battle = 0x022E58E0
    participants = (0x022E24E0, 0x022E2640, 0x022E27A0, 0x022E2900)
    memory.write32(global_config, session)
    memory.write8(global_config + 0x98, int(team_scores is not None))
    memory.write16(battle + 0x04, selected_record.card_id)
    memory.write8(battle + 0x06, owner_participant)
    if landing_result is not None:
        throw_controller = 0x022F1000
        memory.write32(session + 0x298, throw_controller)
        memory.write8(throw_controller + 0x1D2, landing_result)

    scores = [owner_score, opposing_score, 0, 0]
    if owner_participant == 1:
        scores[0], scores[1] = opposing_score, owner_score
    if team_scores is not None:
        owner_teammate_score, opposing_teammate_score = team_scores
        scores[2] = owner_teammate_score
        scores[3] = opposing_teammate_score
    teammate_indices = (2, 3, 0, 1)
    for index, participant in enumerate(participants):
        memory.write32(session + 0x0C + index * 4, participant)
        memory.write8(participant + 0xEE, scores[index])
        memory.write8(participant + 0xF2, teammate_indices[index])
        if ai_owner and index == owner_participant:
            memory.write32(participant + 0xC8, 0x022F1000)

    for record_index, participant_index in enumerate((0, 1)):
        descriptor = session + 0x7C + record_index * 20
        mapped_participant = participant_index
        if record_index == current_participant:
            mapped_participant = (
                descriptor_participant_override
                if descriptor_participant_override is not None
                else participant_index
            )
        memory.write8(descriptor + 0x0E, 0)
        memory.write8(descriptor + 0x0F, mapped_participant)
        memory.write8(session + 0x28D + record_index, record_index)

        source = participants[participant_index] + 0x0C
        source_core = _source_core_for_compressed(compressed_core_g)
        source_modifier = mutable_modifier_g if participant_index == current_participant else 0
        memory.write16(source + 0x04, source_core)
        memory.write16(source + 0x06, source_modifier)
        memory.write8(source + 0x09, attribute_id)

        record_base = battle + record_index * 20
        record_attribute = attribute_id if participant_index == current_participant else 0
        memory.write8(
            record_base + 0x19,
            (participant_index << 4) | record_attribute,
        )
        base_snapshot = compressed_core_g + source_modifier
        memory.write16(record_base + 0x0C, base_snapshot)
        memory.write16(record_base + 0x10, base_snapshot)

    cpu = ArmCpu(memory)
    cpu.registers[4] = current_participant
    cpu.registers[5] = battle + current_participant * 20
    cpu.registers[6] = battle
    cpu.registers[13] = 0x027FF000

    def legacy_gate_lookup(machine: ArmCpu) -> None:
        machine.registers[0] = 10
        machine.registers[15] = machine.registers[14]

    cpu.external_calls[0x02065BF4] = legacy_gate_lookup
    cpu.run(
        module.symbols["g2_gate_bonus_hook"].address,
        stop_addresses={0x0223D278},
    )
    record_base = battle + current_participant * 20
    gate_bonus = memory.read16(record_base + 0x12)
    fallback_flag = cpu.registers[3]

    cpu.registers[1] = gate_bonus
    cpu.registers[2] = memory.read16(record_base + 0x0C)
    cpu.registers[5] = record_base
    cpu.run(
        module.symbols["g2_context_store_hook"].address,
        stop_addresses={0x0223D290},
    )
    return gate_bonus, memory.read16(record_base + 0x0E), fallback_flag


@pytest.mark.parametrize(
    ("compressed_core_g", "attribute_id", "behind", "expected_bonus"),
    (
        (190, 0, False, 74),
        (190, 1, False, 104),
        (190, 0, True, 114),
        (190, 1, True, 144),
        (525, 0, False, 101),
        (525, 1, False, 131),
        (525, 0, True, 141),
        (525, 1, True, 171),
    ),
)
def test_emitted_gate_calculation_matches_approved_vectors(
    compressed_core_g: int,
    attribute_id: int,
    behind: bool,
    expected_bonus: int,
) -> None:
    owner_score, opposing_score = (1, 2) if behind else (2, 1)
    bonus, target, fallback_flag = _execute_emitted_gate_case(
        compressed_core_g=compressed_core_g,
        attribute_id=attribute_id,
        owner_score=owner_score,
        opposing_score=opposing_score,
    )
    assert bonus == expected_bonus
    assert target == compressed_core_g + expected_bonus
    assert fallback_flag == 1


def test_emitted_gate_rider_never_applies_to_non_owner_or_tied_owner() -> None:
    non_owner = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=1,
        owner_score=1,
        opposing_score=2,
        current_participant=1,
    )
    tied_owner = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=1,
        owner_score=2,
        opposing_score=2,
    )
    assert non_owner == (104, 294, 1)
    assert tied_owner == (104, 294, 1)


def test_emitted_gate_uses_reciprocal_team_scores_and_ai_owner_identically() -> None:
    bonus, target, fallback_flag = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=0,
        owner_score=1,
        opposing_score=1,
        team_scores=(0, 1),
        ai_owner=True,
    )
    assert (bonus, target, fallback_flag) == (114, 304, 1)


def test_emitted_gate_invalid_descriptor_mapping_uses_complete_legacy_fallback() -> None:
    bonus, target, fallback_flag = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=1,
        owner_score=1,
        opposing_score=2,
        descriptor_participant_override=1,
    )
    assert (bonus, target, fallback_flag) == (100, 290, 0)


def test_emitted_gate_invalid_attribute_uses_complete_legacy_fallback() -> None:
    bonus, target, fallback_flag = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=6,
        owner_score=1,
        opposing_score=2,
    )
    assert (bonus, target, fallback_flag) == (100, 290, 0)



def test_emitted_generic_control_target_and_drawback_match_host() -> None:
    from dataclasses import replace

    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.record import GateArchetype, GateConditionId, GateEffectId, GateTargetMode
    from bakugan_ds.gates.system2 import GateCalculationContext, calculate_gate_bonus

    record = replace(
        approved_juggernoid_record(),
        card_id=20,
        archetype=GateArchetype.CONTROL,
        flat_bonus_g=50,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        condition_id=GateConditionId.OWNER_AHEAD,
        effect_id=GateEffectId.ADD_SIGNED_G,
        effect_value=50,
        drawback_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
        drawback_value=25,
        target_mode=GateTargetMode.GATE_OWNER,
    )
    host = calculate_gate_bonus(
        record,
        GateCalculationContext(190, 0, 0, 0, 2, 1, 20),
    )
    emitted = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=0,
        owner_score=2,
        opposing_score=1,
        record=record,
    )
    assert emitted == (host.effective_gate_bonus, host.target_total_g, 1)


def test_emitted_generic_non_owner_target_matches_host() -> None:
    from dataclasses import replace

    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.record import GateArchetype, GateConditionId, GateEffectId, GateTargetMode
    from bakugan_ds.gates.system2 import GateCalculationContext, calculate_gate_bonus

    record = replace(
        approved_juggernoid_record(),
        card_id=21,
        archetype=GateArchetype.CONTROL,
        flat_bonus_g=80,
        percent_q8_8=-16,
        attribute_modifiers=(-20, 0, 20, 0, 0, 0),
        condition_id=GateConditionId.NONE,
        effect_id=GateEffectId.SUBTRACT_MAGNITUDE_G,
        effect_value=30,
        target_mode=GateTargetMode.GATE_NON_OWNER,
    )
    host = calculate_gate_bonus(
        record,
        GateCalculationContext(190, 0, 1, 0, 1, 1, 21),
    )
    emitted = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=0,
        owner_score=1,
        opposing_score=1,
        current_participant=1,
        owner_participant=0,
        record=record,
    )
    assert emitted == (host.effective_gate_bonus, host.target_total_g, 1)


def test_emitted_landing_condition_uses_confirmed_throw_result() -> None:
    from dataclasses import replace

    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.record import GateArchetype, GateConditionId, GateTargetMode

    record = replace(
        approved_juggernoid_record(),
        card_id=22,
        archetype=GateArchetype.CONTROL,
        flat_bonus_g=60,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        condition_id=GateConditionId.LANDING_GATE_CARD_WON,
        target_mode=GateTargetMode.CURRENT_COMBATANT,
    )
    won = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=0,
        owner_score=1,
        opposing_score=1,
        record=record,
        landing_result=1,
    )
    other = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=0,
        owner_score=1,
        opposing_score=1,
        record=record,
        landing_result=2,
    )
    missing = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=0,
        owner_score=1,
        opposing_score=1,
        record=record,
    )
    assert won == (100, 290, 1)
    assert other == (60, 250, 1)
    assert missing == (100, 290, 0)

def test_emitted_context_store_clamps_system2_total_but_not_legacy_path() -> None:
    from tests.support.arm32_interpreter import ArmCpu, SparseMemory

    module = build_milestone_6c_module()
    memory = SparseMemory()
    memory.map(MODULE_BASE, module.image)
    record = 0x022E58E0

    system2 = ArmCpu(memory)
    system2.registers[1] = 100
    system2.registers[2] = 0xFFFA
    system2.registers[3] = 1
    system2.registers[5] = record
    system2.run(
        module.symbols["g2_context_store_hook"].address,
        stop_addresses={0x0223D290},
    )
    assert memory.read16(record + 0x0E) == 0xFFFF

    legacy = ArmCpu(memory)
    legacy.registers[1] = 100
    legacy.registers[2] = 0xFFFA
    legacy.registers[3] = 0
    legacy.registers[5] = record + 0x14
    legacy.run(
        module.symbols["g2_context_store_hook"].address,
        stop_addresses={0x0223D290},
    )
    assert memory.read16(record + 0x14 + 0x0E) == ((0xFFFA + 100) & 0xFFFF)


def test_emitted_percentage_excludes_mutable_modifier_from_scaling() -> None:
    bonus, target, fallback_flag = _execute_emitted_gate_case(
        compressed_core_g=190,
        attribute_id=0,
        owner_score=2,
        opposing_score=1,
        mutable_modifier_g=30,
    )
    assert (bonus, target, fallback_flag) == (74, 294, 1)


def test_emitted_gate_is_owner_symmetric_and_order_independent() -> None:
    owner_first = {
        participant: _execute_emitted_gate_case(
            compressed_core_g=190,
            attribute_id=1,
            owner_score=1,
            opposing_score=2,
            current_participant=participant,
        )
        for participant in (0, 1)
    }
    owner_second = {
        participant: _execute_emitted_gate_case(
            compressed_core_g=190,
            attribute_id=1,
            owner_score=1,
            opposing_score=2,
            current_participant=participant,
            owner_participant=1,
        )
        for participant in (1, 0)
    }
    assert owner_first == {0: (144, 334, 1), 1: (104, 294, 1)}
    assert owner_second == {1: (144, 334, 1), 0: (104, 294, 1)}


def _execute_emitted_selector_case(
    *,
    seed: int,
    gate_id: int = 19,
    legacy_type: int = 2,
    weighted_override: int | None = None,
    cache_valid: bool = True,
) -> tuple[int, int, int, int, bytes, int]:
    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.history import weighted_index, weighted_roll_from_state
    from bakugan_ds.gates.loader import build_cache
    from tests.support.arm32_interpreter import ArmCpu, SparseMemory

    module = build_milestone_6c_module()
    memory = SparseMemory()
    memory.map(MODULE_BASE, module.image)
    memory.map(CACHE_ADDRESS, build_cache(approved_juggernoid_record(), arena_entry=0))
    if not cache_valid:
        memory.write8(CACHE_ADDRESS + 0x2A, 0)
    battle = 0x022E58E0
    memory.write16(battle + 0x04, gate_id)
    before_history = bytes(memory.read8(CACHE_ADDRESS + 0x38 + index) for index in range(4))

    calls = {"weighted": 0, "legacy": 0}
    rng_state = seed
    weighted_pointer = 0

    cpu = ArmCpu(memory)
    cpu.registers[0] = battle
    cpu.registers[13] = 0x027FF000
    cpu.registers[14] = 0

    def weighted(machine: ArmCpu) -> None:
        nonlocal rng_state, weighted_pointer
        calls["weighted"] += 1
        assert machine.registers[0] == 6
        weighted_pointer = machine.registers[1]
        weights = tuple(memory.read8(weighted_pointer + index) for index in range(6))
        if weighted_override is None:
            rng_state, roll = weighted_roll_from_state(rng_state, sum(weights))
            machine.registers[0] = weighted_index(weights, roll)
        else:
            machine.registers[0] = weighted_override & 0xFFFFFFFF
        machine.registers[15] = machine.registers[14]

    def legacy(machine: ArmCpu) -> None:
        calls["legacy"] += 1
        machine.registers[0] = legacy_type
        machine.registers[15] = machine.registers[14]

    cpu.external_calls[0x02021A30] = weighted
    cpu.external_calls[0x022433AC] = legacy
    cpu.run(
        module.symbols["g2_selector_hook"].address,
        stop_addresses={0},
    )
    after_history = bytes(memory.read8(CACHE_ADDRESS + 0x38 + index) for index in range(4))
    assert before_history == after_history == b"\0\0\0\0"
    return (
        cpu.registers[0],
        rng_state,
        calls["weighted"],
        calls["legacy"],
        after_history,
        weighted_pointer,
    )


@pytest.mark.parametrize("seed", (0, 1, 0x12345678, 0xFFFFFFFFFFFFFFFF))
def test_emitted_selector_matches_host_weighted_selection(seed: int) -> None:
    from bakugan_ds.gates.authoring import approved_juggernoid_record
    from bakugan_ds.gates.selector import select_system2_battle_type

    host = select_system2_battle_type(
        approved_juggernoid_record(),
        constructor_type=-1,
        scripted_override=None,
        rng_state=seed,
        legacy_type=2,
    )
    result = _execute_emitted_selector_case(seed=seed)
    assert result[:4] == (host.final_type, host.next_rng_state, 1, 0)
    assert result[5] == CACHE_ADDRESS + 0x0E


def test_emitted_selector_unrelated_gate_uses_legacy_without_rng() -> None:
    result = _execute_emitted_selector_case(seed=0x1234, gate_id=21, legacy_type=4)
    assert result[:4] == (4, 0x1234, 0, 1)


def test_emitted_selector_invalid_weighted_result_uses_phase_local_legacy() -> None:
    result = _execute_emitted_selector_case(
        seed=0x1234,
        legacy_type=3,
        weighted_override=-1,
    )
    assert result[:4] == (3, 0x1234, 1, 1)


def test_emitted_selector_invalid_cache_uses_legacy_without_rng() -> None:
    result = _execute_emitted_selector_case(
        seed=0x5678,
        legacy_type=1,
        cache_valid=False,
    )
    assert result[:4] == (1, 0x5678, 0, 1)


def test_emitted_selector_out_of_range_result_uses_phase_local_legacy() -> None:
    result = _execute_emitted_selector_case(
        seed=0x9ABC,
        legacy_type=4,
        weighted_override=6,
    )
    assert result[:4] == (4, 0x9ABC, 1, 1)
