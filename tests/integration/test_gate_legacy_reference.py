from pathlib import Path

import pytest

from bakugan_ds.gates.io import load_json_object
from bakugan_ds.gates.legacy import legacy_spec_from_dict, parse_legacy_table
from bakugan_ds.gates.runtime_image import (
    load_runtime_arm9,
    load_workspace_arm9,
    map_runtime_region,
)
from bakugan_ds.workspace.manifest import WorkspaceManifest

METADATA_PATH = Path("analysis/gates/legacy-table-metadata.json")


@pytest.mark.integration
def test_legacy_gate_table_matches_confirmed_runtime_metadata(
    reference_runtime_arm9: Path,
    reference_workspace: tuple[Path, WorkspaceManifest],
) -> None:
    payload = load_json_object(METADATA_PATH)
    spec = legacy_spec_from_dict(payload)
    workspace, _ = reference_workspace
    runtime_image = load_runtime_arm9(reference_runtime_arm9)
    workspace_image = load_workspace_arm9(workspace)

    mapping = map_runtime_region(
        runtime_image,
        workspace_image,
        spec.runtime_address,
        spec.table_size,
    )
    records = parse_legacy_table(runtime_image, spec)

    expected_mapping = payload["mapping"]
    assert isinstance(expected_mapping, dict)
    assert mapping.runtime_offset == expected_mapping["runtime_offset"]
    assert mapping.decoded_offset == expected_mapping["decoded_offset"]
    assert mapping.decoded_sha256 == expected_mapping["decoded_sha256"]
    assert mapping.stored_sha256 == expected_mapping["stored_sha256"]
    assert mapping.directly_patchable is expected_mapping["directly_patchable"]
    assert len(records) == spec.record_count == 213
    assert payload["complete_table_committed"] is False

    for control_case in spec.control_cases:
        assert records[control_case.card_id].bonuses_g[control_case.attribute_id] == (
            control_case.expected_bonus_g
        )
