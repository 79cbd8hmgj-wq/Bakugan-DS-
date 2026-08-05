from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds.gates.loader import CACHE_ADDRESS, CACHE_SIZE, SYSTEM2_MODULE_SIZE
from bakugan_ds.gates.runtime_module import MODULE_BASE
from bakugan_ds.gates.runtime_module_6d import build_milestone_6d_module
from bakugan_ds.workspace.manifest import WorkspaceManifest

EXPECTED_MODULE_SHA256 = "8fa90c244d3710479e94903e099f9dbbe71b5ce8d86c52603383d2e4f42e7a1c"
PROTECTED_CORE_G_RANGES = (
    (0x23C18, 0x23C1C),
    (0x23CB0, 0x23CF8),
    (0x23D78, 0x23D7C),
)


@pytest.mark.integration
def test_exact_overlay_supports_milestone_6d_hooks_without_module_growth(
    reference_workspace: tuple[Path, WorkspaceManifest],
) -> None:
    workspace, _manifest = reference_workspace
    overlay = (workspace / "original/decoded/overlays/overlay_007.bin").read_bytes()
    module = build_milestone_6d_module()

    assert module.sha256 == EXPECTED_MODULE_SHA256
    assert len(module.image) == SYSTEM2_MODULE_SIZE == 0x8000
    assert MODULE_BASE == 0x0228BC20
    assert MODULE_BASE + len(module.image) == CACHE_ADDRESS == 0x02293C20
    assert CACHE_ADDRESS + CACHE_SIZE == 0x02293C60
    assert set(module.symbols) >= {
        "g2_evaluate_condition",
        "g2_matches_target",
        "g2_apply_effect",
        "g2_calculate_gate_bonus",
        "g2_select_battle_type",
    }

    for hook in module.hook_replacements:
        start = hook.component_offset
        end = start + len(hook.expected)
        assert overlay[start:end] == hook.expected
        assert hook.rollback.strip()
        for protected_start, protected_end in PROTECTED_CORE_G_RANGES:
            assert end <= protected_start or start >= protected_end

    occupied: list[tuple[int, int, str]] = []
    for name, symbol in module.symbols.items():
        start = symbol.address
        end = symbol.address + symbol.size
        assert MODULE_BASE <= start < end <= CACHE_ADDRESS
        for old_start, old_end, old_name in occupied:
            assert end <= old_start or start >= old_end, (name, old_name)
        occupied.append((start, end, name))
