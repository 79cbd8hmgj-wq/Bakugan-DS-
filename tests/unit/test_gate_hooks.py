from __future__ import annotations

import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.hooks import (
    HookPurpose,
    HookSite,
    normalize_hook_capture,
    validate_hook_sites,
)
from bakugan_ds.gates.model import Confidence


def site(purpose: HookPurpose, *, offset: int) -> HookSite:
    return HookSite(
        purpose=purpose,
        component="overlay_0007",
        address=0x02219440 + offset,
        component_offset=offset,
        instruction_length=4,
        expected_bytes_sha256="a" * 64,
        calling_convention="ARM AAPCS-like game convention",
        live_registers=("r0",),
        stack_assumptions="stack is 8-byte aligned",
        overwritten_behavior="one displaced instruction is replayed",
        return_address=0x02219440 + offset + 4,
        code_space_strategy="expanded overlay module",
        core_g_compatible=True,
        rollback="restore original bytes and clear cache",
        confidence=Confidence.CONFIRMED,
        evidence="static disassembly and runtime evidence",
    )


def all_sites() -> tuple[HookSite, ...]:
    return (
        site(HookPurpose.GATE_BONUS, offset=0x23E18),
        site(HookPurpose.BATTLE_TYPE_SELECTOR, offset=0x24F10),
        site(HookPurpose.CONTEXT_ACCESS, offset=0x23E48),
        site(HookPurpose.EXPANDED_DATA_LOOKUP, offset=0x29F6C),
    )


def test_hook_validation_requires_all_four_purposes() -> None:
    with pytest.raises(WorkspaceError, match="missing hook purposes"):
        validate_hook_sites(all_sites()[:-1])


def test_hook_validation_rejects_core_g_overlap() -> None:
    sites = list(all_sites())
    sites[0] = site(HookPurpose.GATE_BONUS, offset=0x23CB0)
    with pytest.raises(WorkspaceError, match="protected core-G"):
        validate_hook_sites(tuple(sites))


def test_hook_validation_rejects_invalid_hash() -> None:
    bad = site(HookPurpose.GATE_BONUS, offset=0x23E18)
    bad = HookSite(**{**bad.__dict__, "expected_bytes_sha256": "bad"})
    with pytest.raises(WorkspaceError, match="SHA-256"):
        validate_hook_sites((bad, *all_sites()[1:]))


def test_committed_hook_capture_normalizes() -> None:
    payload = json.loads(Path("analysis/gates/hook-feasibility.json").read_text())
    sites = normalize_hook_capture(payload)
    validate_hook_sites(sites)
    assert {site.purpose for site in sites} == set(HookPurpose)
