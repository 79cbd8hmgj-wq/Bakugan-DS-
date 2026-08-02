from __future__ import annotations

import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.context import confirmed_hook_context, load_context_fields


def field(
    name: str,
    *,
    confidence: str = "confirmed",
    safe: bool = True,
    initialization: str = "initialized by constructor",
    reset: str = "discarded with battle object",
) -> dict[str, object]:
    return {
        "name": name,
        "width_bits": 16,
        "signed": False,
        "owner_structure": "combatant_record",
        "access": "+0x10",
        "lifetime": "battle",
        "initialization": initialization,
        "reset": reset,
        "safe_for_hook": safe,
        "confidence": confidence,
        "evidence": f"evidence for {name}",
        "exclusion_reason": "unresolved semantics" if confidence != "confirmed" else "",
    }


def test_only_confirmed_safe_initialized_fields_enter_hook_context(tmp_path: Path) -> None:
    path = tmp_path / "context.json"
    path.write_text(
        json.dumps(
            {
                "fields": [
                    field("compressed_core_g"),
                    field("gate_owner", confidence="candidate", safe=False),
                    field("missing_reset", reset=""),
                ]
            }
        ),
        encoding="utf-8",
    )
    fields = load_context_fields(path)
    assert [item.name for item in confirmed_hook_context(fields)] == ["compressed_core_g"]


def test_context_rejects_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "context.json"
    path.write_text(json.dumps({"fields": [field("gate_bonus"), field("gate_bonus")]}))
    with pytest.raises(WorkspaceError, match="duplicate battle-context field"):
        load_context_fields(path)


def test_context_rejects_unsupported_width(tmp_path: Path) -> None:
    bad = field("bad_width")
    bad["width_bits"] = 64
    path = tmp_path / "context.json"
    path.write_text(json.dumps({"fields": [bad]}))
    with pytest.raises(WorkspaceError, match="width"):
        load_context_fields(path)


def test_candidate_field_requires_exclusion_reason(tmp_path: Path) -> None:
    bad = field("gate_owner", confidence="candidate", safe=False)
    bad["exclusion_reason"] = ""
    path = tmp_path / "context.json"
    path.write_text(json.dumps({"fields": [bad]}))
    with pytest.raises(WorkspaceError, match="exclusion reason"):
        load_context_fields(path)
