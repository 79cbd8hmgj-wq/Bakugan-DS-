from __future__ import annotations

import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.legacy import (
    export_legacy_table,
    legacy_metadata,
    legacy_spec_from_dict,
    parse_legacy_table,
)
from bakugan_ds.gates.model import Confidence, LegacyGateTableSpec
from bakugan_ds.gates.runtime_image import RuntimeStoredMapping, load_runtime_arm9
from bakugan_ds.workspace.manifest import sha256_bytes

ATTRIBUTES = tuple(f"attribute_{index}" for index in range(6))


def synthetic_spec(
    *,
    address: int = 0x02000000,
    count: int = 1,
    width: int = 1,
    signed: bool = False,
    region_sha256: str,
) -> LegacyGateTableSpec:
    return LegacyGateTableSpec(
        profile_id="b6re_rev0",
        runtime_address=address,
        element_width=width,
        signed=signed,
        record_stride=width * 6,
        record_count=count,
        attribute_order=ATTRIBUTES,
        region_sha256=region_sha256,
        confidence=Confidence.CONFIRMED,
        control_cases=(),
    )


def test_unsigned_rows_scale_to_display_g(tmp_path: Path) -> None:
    path = tmp_path / "runtime.bin"
    path.write_bytes(bytes([10, 8, 12, 9, 7, 11]))
    spec = synthetic_spec(region_sha256=sha256_bytes(path.read_bytes()))

    record = parse_legacy_table(load_runtime_arm9(path), spec)[0]

    assert record.card_id == 0
    assert record.raw_values == (10, 8, 12, 9, 7, 11)
    assert record.bonuses_g == (100, 80, 120, 90, 70, 110)


def test_signed_rows_use_little_endian_signed_values(tmp_path: Path) -> None:
    path = tmp_path / "runtime.bin"
    path.write_bytes(bytes([0xFE, 0, 1, 2, 3, 4]))
    spec = synthetic_spec(
        signed=True,
        region_sha256=sha256_bytes(path.read_bytes()),
    )

    record = parse_legacy_table(load_runtime_arm9(path), spec)[0]

    assert record.raw_values == (-2, 0, 1, 2, 3, 4)
    assert record.bonuses_g == (-20, 0, 10, 20, 30, 40)


def test_parser_rejects_stale_region_hash(tmp_path: Path) -> None:
    path = tmp_path / "runtime.bin"
    path.write_bytes(bytes([1, 2, 3, 4, 5, 6]))
    spec = synthetic_spec(region_sha256="a" * 64)

    with pytest.raises(WorkspaceError, match="region hash"):
        parse_legacy_table(load_runtime_arm9(path), spec)


def test_spec_loader_rejects_missing_fields() -> None:
    with pytest.raises(WorkspaceError, match="invalid legacy Gate metadata"):
        legacy_spec_from_dict({"profile_id": "b6re_rev0"})


def test_metadata_excludes_complete_table_rows(tmp_path: Path) -> None:
    path = tmp_path / "runtime.bin"
    path.write_bytes(bytes([1, 2, 3, 4, 5, 6]))
    image = load_runtime_arm9(path)
    spec = synthetic_spec(region_sha256=sha256_bytes(path.read_bytes()))
    mapping = RuntimeStoredMapping(
        runtime_address=0x02000000,
        runtime_offset=0,
        workspace_component="arm9",
        decoded_offset=0,
        mapping_kind="direct",
        decoded_sha256=image.sha256,
        stored_sha256=image.sha256,
        directly_patchable=True,
    )

    payload = legacy_metadata(image, spec, mapping)

    assert payload["complete_table_committed"] is False
    assert "records" not in payload
    assert payload["table_size"] == 6


def test_export_writes_local_records_deterministically(tmp_path: Path) -> None:
    path = tmp_path / "runtime.bin"
    path.write_bytes(bytes([10, 8, 12, 9, 7, 11]))
    spec = synthetic_spec(region_sha256=sha256_bytes(path.read_bytes()))
    records = parse_legacy_table(load_runtime_arm9(path), spec)
    output = tmp_path / "work" / "reports" / "gates" / "legacy-table.json"

    export_legacy_table(output, records, spec)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert output.read_text(encoding="utf-8").endswith("\n")
    assert payload["local_only"] is True
    assert payload["records"][0]["bonuses_g"] == [100, 80, 120, 90, 70, 110]
