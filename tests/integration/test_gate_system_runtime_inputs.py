from pathlib import Path

import pytest

from bakugan_ds.gates.runtime_image import (
    load_runtime_arm9,
    load_workspace_arm9,
    map_runtime_region,
)
from bakugan_ds.workspace.manifest import WorkspaceManifest

GATE_LOOKUP_HELPER = 0x02065BF4


@pytest.mark.integration
def test_gate_lookup_helper_matches_runtime_and_workspace_arm9(
    reference_runtime_arm9: Path,
    reference_workspace: tuple[Path, WorkspaceManifest],
) -> None:
    workspace, _ = reference_workspace
    mapping = map_runtime_region(
        load_runtime_arm9(reference_runtime_arm9),
        load_workspace_arm9(workspace),
        GATE_LOOKUP_HELPER,
        16,
    )

    assert mapping.runtime_offset == GATE_LOOKUP_HELPER - 0x02000000
    assert mapping.decoded_offset == mapping.runtime_offset


@pytest.mark.integration
def test_gate_hook_sites_match_exact_overlay_and_avoid_core_g_patch(
    reference_workspace: tuple[Path, WorkspaceManifest],
) -> None:
    import hashlib
    import json

    from bakugan_ds.gates.hooks import normalize_hook_capture, validate_hook_sites

    workspace, _ = reference_workspace
    overlay = (workspace / "original/decoded/overlays/overlay_007.bin").read_bytes()
    payload = json.loads(Path("analysis/gates/hook-feasibility.json").read_text())
    sites = normalize_hook_capture(payload)
    validate_hook_sites(sites)

    for site in sites:
        assert site.component == "overlay_0007"
        region = overlay[
            site.component_offset : site.component_offset + site.instruction_length
        ]
        assert hashlib.sha256(region).hexdigest() == site.expected_bytes_sha256

    patch = json.loads(Path("patches/core-g-compression-400.json").read_text())
    core_ranges = []
    for item in patch["patches"]:
        start = item["offset"]
        core_ranges.append(range(start, start + len(bytes.fromhex(item["replacement"]))))
    for site in sites:
        site_range = range(
            site.component_offset,
            site.component_offset + site.instruction_length,
        )
        assert all(
            site_range.stop <= protected.start or protected.stop <= site_range.start
            for protected in core_ranges
        )
