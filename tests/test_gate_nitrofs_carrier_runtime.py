from __future__ import annotations

import json
from pathlib import Path

ARTIFACT = Path("analysis/gates/nitrofs-carrier-runtime.json")


def load_artifact() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_carrier_runtime_uses_exact_reference_file() -> None:
    payload = load_artifact()
    carrier = payload["carrier"]
    assert isinstance(carrier, dict)
    assert carrier["file_id"] == 2762
    assert carrier["path"] == "font/mes_CardName.mes"
    assert carrier["raw_size"] == 2840
    assert carrier["raw_sha256"] == (
        "76a03522a5031762eb51d07b72a19331bc06a5b6dc0eab60e227a199466d4c4e"
    )


def test_carrier_runtime_confirms_complete_io_sequence() -> None:
    payload = load_artifact()
    assert payload["status"] == "confirmed"
    fs_file = payload["fs_file"]
    assert isinstance(fs_file, dict)
    assert fs_file["size"] == 72
    assert fs_file["address"] == 0x020D5440
    assert fs_file["archive_after_open"] == 0x020BFCB4
    assert fs_file["own_id_after_open"] == 2762
    assert fs_file["bottom_after_open"] - fs_file["top_after_open"] == 2840

    operations = payload["operations"]
    assert isinstance(operations, list)
    assert [operation["name"] for operation in operations] == [
        "FS_OpenFileFast",
        "FS_SeekFile",
        "FS_ReadFile",
        "FS_ReadFile",
        "FS_CloseFile",
    ]
    assert [operation["function"] for operation in operations] == [
        0x0200AA24,
        0x0200AC40,
        0x0200AC30,
        0x0200AC30,
        0x0200AADC,
    ]
    assert [operation["return_value"] for operation in operations] == [1, 1, 4, 2836, 1]


def test_carrier_read_is_clamped_to_file_bottom() -> None:
    payload = load_artifact()
    operations = payload["operations"]
    assert isinstance(operations, list)
    first_read = operations[2]
    second_read = operations[3]
    assert first_read["arguments"]["length"] == 4
    assert first_read["return_value"] == 4
    assert first_read["position_after"] - first_read["position_before"] == 4
    assert second_read["arguments"]["length"] == 2840
    assert second_read["return_value"] == 2836
    assert second_read["position_after"] - second_read["position_before"] == 2836
    assert second_read["position_after"] == payload["fs_file"]["bottom_after_open"]


def test_carrier_runtime_keeps_only_cache_lifecycle_unresolved() -> None:
    payload = load_artifact()
    assert payload["unresolved"] == [
        "Live System 2.0 cache initialization",
        "Live System 2.0 cache invalidation at battle completion",
    ]
