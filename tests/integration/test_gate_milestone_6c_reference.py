from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from bakugan_ds.gates.arm32 import decode_branch_target
from bakugan_ds.gates.runtime_module import (
    MODULE_BASE,
    build_milestone_6c_module,
)


def test_exact_overlay_hook_guards_and_module_layout() -> None:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if not value:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Milestone 6C reference tests")
    overlay = Path(value).read_bytes()
    module = build_milestone_6c_module()

    assert hashlib.sha256(overlay).hexdigest() == (
        "82904b4ec35e5eeae243324259e0c984ed8a0f3be2c4c5992d35d71249c194e1"
    )
    for hook in module.hook_replacements:
        actual = overlay[
            hook.component_offset : hook.component_offset + len(hook.expected)
        ]
        assert actual == hook.expected
    assert len(module.image) == 0x8000
    assert module.symbols["g2_clear_cache"].address == 0x0228BC20


def test_task_9_live_calculation_stays_inside_reserved_module() -> None:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if not value:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Milestone 6C reference tests")
    overlay = Path(value).read_bytes()
    module = build_milestone_6c_module()

    calculation = module.symbols["g2_calculate_gate_bonus"]
    context_store = module.symbols["g2_context_store_hook"]
    assert calculation.address == 0x0228C360
    assert calculation.address + calculation.size <= 0x0228C720
    assert context_store.address == 0x0228C760
    assert context_store.address + context_store.size <= 0x0228C790

    protected = (
        (0x23C18, bytes.fromhex("0c70a0e3")),
        (
            0x23CB0,
            bytes.fromhex(
                "b420d1e1b610d1e1011082e0bc10c6e1b410d0e1b600d0e1000081e0"
                "b002c6e1bc00d6e1b001c6e1b002d6e10ab0a0e30b70a0e1b402c6e1"
                "b241c6e1b642c6e1b641c6e1ba42c6e1"
            ),
        ),
        (0x23D78, bytes.fromhex("0b80a0e1")),
    )
    for offset, expected in protected:
        assert overlay[offset : offset + len(expected)] == expected


def test_exact_overlay_module_activates_task_9_gate_path() -> None:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if not value:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Milestone 6C reference tests")
    overlay = Path(value).read_bytes()
    module = build_milestone_6c_module()

    gate_hook = next(
        hook for hook in module.hook_replacements if hook.target_symbol == "g2_gate_bonus_hook"
    )
    context_hook = next(
        hook
        for hook in module.hook_replacements
        if hook.target_symbol == "g2_context_store_hook"
    )
    assert overlay[
        gate_hook.component_offset : gate_hook.component_offset + len(gate_hook.expected)
    ] == gate_hook.expected
    assert overlay[
        context_hook.component_offset : context_hook.component_offset + len(context_hook.expected)
    ] == context_hook.expected

    gate_entry = module.symbols["g2_gate_bonus_hook"]
    gate_word = int.from_bytes(
        module.image[
            gate_entry.address - MODULE_BASE : gate_entry.address - MODULE_BASE + 4
        ],
        "little",
    )
    assert decode_branch_target(gate_entry.address, gate_word) == (
        module.symbols["g2_calculate_gate_bonus"].address
    )
    assert module.symbols["g2_calculate_gate_bonus"].size == 0x300
    assert module.symbols["g2_calculate_gate_bonus"].code_size > 0x2C0
    assert module.symbols["g2_context_store_hook"].size > 8


def test_task_10_preserves_explicit_and_scripted_selector_precedence() -> None:
    value = os.environ.get("BAKUGAN_DS_OVERLAY7")
    if not value:
        pytest.skip("set BAKUGAN_DS_OVERLAY7 to run Milestone 6C reference tests")
    overlay = Path(value).read_bytes()
    module = build_milestone_6c_module()
    by_name = {hook.name: hook for hook in module.hook_replacements}

    selector_hook = by_name["battle_type_selector"]
    assert selector_hook.address == 0x0223E350
    assert len(selector_hook.expected) == 4

    constructor_start = 0x0223E338 - 0x02219440
    constructor_end = 0x0223E358 - 0x02219440
    assert hashlib.sha256(overlay[constructor_start:constructor_end]).hexdigest() == (
        "b1fb46f46149a2cca760289f5d8cdb1d653010736dc2d861ee56e5ab68cfd56e"
    )

    scripted_start = 0x022417A8 - 0x02219440
    scripted_end = 0x02241840 - 0x02219440
    assert hashlib.sha256(overlay[scripted_start:scripted_end]).hexdigest() == (
        "cb0e50a7e140fd1a7804cdbf40a49a46f8bb690b56a082561fd836f4f892e83f"
    )
