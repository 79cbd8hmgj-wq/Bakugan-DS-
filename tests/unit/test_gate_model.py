from __future__ import annotations

import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.io import load_json_object, write_evidence
from bakugan_ds.gates.model import (
    AddressRef,
    Confidence,
    GateControlCase,
    LegacyGateTableSpec,
)

ATTRIBUTES = ("pyrus", "aquos", "subterra", "haos", "darkus", "ventus")


def make_spec(**overrides: object) -> LegacyGateTableSpec:
    values: dict[str, object] = {
        "profile_id": "b6re_rev0",
        "runtime_address": 0x020A15AC,
        "element_width": 1,
        "signed": False,
        "record_stride": 6,
        "record_count": 2,
        "attribute_order": ATTRIBUTES,
        "region_sha256": "a" * 64,
        "confidence": Confidence.CONFIRMED,
        "control_cases": (
            GateControlCase(0, 1, 100, "tutorial-player"),
        ),
    }
    values.update(overrides)
    return LegacyGateTableSpec(**values)  # type: ignore[arg-type]


def test_gate_spec_rejects_wrong_stride() -> None:
    spec = make_spec(record_stride=5)
    with pytest.raises(WorkspaceError, match="record stride"):
        spec.validate()


def test_gate_spec_requires_six_unique_attributes() -> None:
    spec = make_spec(attribute_order=("pyrus",) * 6)
    with pytest.raises(WorkspaceError, match="unique"):
        spec.validate()


def test_gate_spec_rejects_control_case_outside_record_count() -> None:
    spec = make_spec(control_cases=(GateControlCase(2, 0, 100, "outside"),))
    with pytest.raises(WorkspaceError, match="card ID"):
        spec.validate()


def test_address_and_control_case_validation() -> None:
    AddressRef("arm9", 0x02065BF4, 0x65BF4, Confidence.CONFIRMED, "watchpoint").validate()
    with pytest.raises(WorkspaceError, match="evidence"):
        AddressRef("arm9", 1, 1, Confidence.CANDIDATE, "").validate()
    with pytest.raises(WorkspaceError, match="attribute ID"):
        GateControlCase(0, 6, 100, "bad-attribute").validate()


def test_confidence_values_are_strict() -> None:
    assert Confidence("confirmed") is Confidence.CONFIRMED
    with pytest.raises(ValueError):
        Confidence("CONFIRMED")


def test_evidence_io_is_deterministic_and_requires_object(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "evidence.json"
    write_evidence(path, {"z": 1, "a": {"confidence": Confidence.PROBABLE}})
    assert path.read_text(encoding="utf-8") == (
        '{\n  "a": {\n    "confidence": "probable"\n  },\n  "z": 1\n}\n'
    )
    assert load_json_object(path) == {"a": {"confidence": "probable"}, "z": 1}

    array_path = tmp_path / "array.json"
    array_path.write_text(json.dumps([1, 2]), encoding="utf-8")
    with pytest.raises(WorkspaceError, match="JSON object"):
        load_json_object(array_path)
