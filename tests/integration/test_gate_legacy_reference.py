import hashlib
from pathlib import Path

import pytest

from bakugan_ds.gates.identity import attribute_order_from_messages, parse_indexed_messages
from bakugan_ds.gates.io import load_json_object
from bakugan_ds.gates.legacy import legacy_spec_from_dict, parse_legacy_table
from bakugan_ds.gates.runtime_image import (
    load_runtime_arm9,
    load_workspace_arm9,
    map_runtime_region,
)
from bakugan_ds.workspace.manifest import WorkspaceManifest

METADATA_PATH = Path("analysis/gates/legacy-table-metadata.json")
IDENTITY_PATH = Path("analysis/gates/card-id-evidence.json")


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


@pytest.mark.integration
def test_selected_gate_ids_and_attribute_order_match_rom_resources(
    reference_runtime_arm9: Path,
    reference_workspace: tuple[Path, WorkspaceManifest],
) -> None:
    identity = load_json_object(IDENTITY_PATH)
    workspace, manifest = reference_workspace
    decoded = workspace / "original/decoded/nitrofs"

    card_names_path = decoded / "font/mes_CardName.mes"
    attribute_path = decoded / "font/mes_Bakugan.mes"
    card_names_data = card_names_path.read_bytes()
    attribute_data = attribute_path.read_bytes()
    card_names = parse_indexed_messages(card_names_data)
    attribute_messages = parse_indexed_messages(attribute_data)

    assert len(card_names) == identity["card_name_source"]["entry_count"] == 213
    assert hashlib.sha256(card_names_data).hexdigest() == (
        identity["card_name_source"]["decoded_sha256"]
    )
    assert hashlib.sha256(attribute_data).hexdigest() == (
        identity["attribute_source"]["decoded_sha256"]
    )
    assert list(attribute_order_from_messages(attribute_messages)) == [
        item["name"] for item in identity["attributes"]
    ]

    runtime_image = load_runtime_arm9(reference_runtime_arm9)
    spec = legacy_spec_from_dict(load_json_object(METADATA_PATH))
    records = parse_legacy_table(runtime_image, spec)
    file_by_path = {item.path: item for item in manifest.files}

    selected_rows = identity["selected_rows"]
    assert isinstance(selected_rows, list)
    for selected in selected_rows:
        assert isinstance(selected, dict)
        card_id = selected["card_id"]
        assert card_names[card_id] == selected["label"]
        assert list(records[card_id].raw_values) == selected["raw_values"]
        assert list(records[card_id].bonuses_g) == selected["bonuses_g"]

        asset = selected["graphic_asset"]
        assert isinstance(asset, dict)
        manifest_entry = file_by_path[asset["path"]]
        assert manifest_entry.file_id == asset["file_id"]
        assert manifest_entry.decoded_sha256 == asset["sha256"]
