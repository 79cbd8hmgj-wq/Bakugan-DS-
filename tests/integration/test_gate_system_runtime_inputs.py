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
