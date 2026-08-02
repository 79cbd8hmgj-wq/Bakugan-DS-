from __future__ import annotations

import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.selector import normalize_selector_capture


def base_payload() -> dict[str, object]:
    return {
        "selector": {
            "component": "overlay_0007",
            "runtime_address": "0x022433AC",
            "component_offset": "0x00029F6C",
            "confidence": "confirmed",
            "evidence": "Reads metadata field 2 for selected card.",
        },
        "selection_mode": "fixed_metadata",
        "rng_calls": [],
        "random_range": None,
        "types": [
            {
                "type_id": 0,
                "label": "Scratch",
                "confidence": "confirmed",
                "evidence": "Metadata and dispatch case 0.",
            },
            {
                "type_id": 1,
                "label": "Timing",
                "confidence": "confirmed",
                "evidence": "Metadata and dispatch case 1.",
            },
            {
                "type_id": 3,
                "label": "Spin",
                "confidence": "confirmed",
                "evidence": "Metadata and dispatch case 3.",
            },
        ],
        "inputs": [
            {
                "name": "card_id",
                "source": "battle object selected Gate",
                "influence": "indexes metadata table",
                "confidence": "confirmed",
                "evidence": "Accessor receives global card ID.",
            }
        ],
        "result_storage": {
            "component": "overlay_0007",
            "runtime_address": "0x0223E354",
            "component_offset": "0x00024F14",
            "confidence": "confirmed",
            "evidence": "Stores helper result to object +0x20.",
        },
        "forced_paths": [
            {
                "name": "battle_override_code",
                "source": "battle data +0x07",
                "mapping": {"1": 0, "2": 3},
                "confidence": "confirmed",
                "evidence": "Switch overwrites object +0x20.",
            }
        ],
    }


def test_selector_rejects_duplicate_type_ids() -> None:
    payload = base_payload()
    raw_types = payload["types"]
    assert isinstance(raw_types, list)
    payload["types"] = [raw_types[0], raw_types[0]]
    with pytest.raises(WorkspaceError, match="duplicate battle type ID"):
        normalize_selector_capture(payload)


def test_fixed_metadata_selector_rejects_rng_claims() -> None:
    payload = base_payload()
    payload["random_range"] = [0, 5]
    with pytest.raises(WorkspaceError, match="fixed metadata selector"):
        normalize_selector_capture(payload)


def test_selector_rejects_reversed_random_range() -> None:
    payload = base_payload()
    payload["selection_mode"] = "weighted_random"
    payload["rng_calls"] = [
        {
            "component": "arm9",
            "runtime_address": "0x02000010",
            "component_offset": "0x10",
            "confidence": "confirmed",
            "evidence": "Synthetic RNG call.",
        }
    ]
    payload["random_range"] = [5, 0]
    with pytest.raises(WorkspaceError, match="random range"):
        normalize_selector_capture(payload)


def test_fixed_selector_accepts_no_rng_and_forced_override() -> None:
    evidence = normalize_selector_capture(base_payload())
    evidence.validate()
    assert evidence.selection_mode == "fixed_metadata"
    assert evidence.random_range is None
    assert evidence.rng_calls == ()
    assert [item.type_id for item in evidence.types] == [0, 1, 3]
    assert evidence.forced_paths[0].mapping == ((1, 0), (2, 3))


def test_committed_selector_evidence_normalizes() -> None:
    payload = json.loads(
        Path("analysis/gates/battle-type-selector.json").read_text(encoding="utf-8")
    )
    evidence = normalize_selector_capture(payload)
    assert [item.type_id for item in evidence.types] == list(range(6))
    assert evidence.selection_mode == "fixed_metadata"
