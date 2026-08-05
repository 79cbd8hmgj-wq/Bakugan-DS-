from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.balance import analyze_gate_balance
from bakugan_ds.gates.record import GateArchetype
from bakugan_ds.gates.roster_templates import (
    GateRosterTemplate,
    load_gate_roster_templates,
    parse_gate_roster_templates,
    write_gate_roster_templates,
)
from bakugan_ds.gates.system2 import FallbackReason, record_fallback_reason

TEMPLATES = Path("config/gates/milestone-6e-archetype-templates.json")
LIVE_ARCHETYPES = tuple(
    archetype for archetype in GateArchetype if archetype is not GateArchetype.LEGACY
)


def _payload() -> dict[str, object]:
    return json.loads(TEMPLATES.read_text(encoding="utf-8"))


def test_committed_templates_cover_every_archetype_with_three_valid_variants() -> None:
    templates = load_gate_roster_templates(TEMPLATES)

    assert len(templates) == 21
    assert Counter(template.archetype for template in templates) == {
        archetype: 3 for archetype in LIVE_ARCHETYPES
    }
    assert [
        (int(template.archetype), template.template_id) for template in templates
    ] == sorted(
        (int(template.archetype), template.template_id) for template in templates
    )

    signatures = {template.runtime_signature() for template in templates}
    assert len(signatures) == len(templates)

    for template in templates:
        record = template.instantiate(card_id=103)
        assert record.card_id == 103
        assert GateArchetype(record.archetype) is template.archetype
        assert record_fallback_reason(record) is FallbackReason.NONE
        report = analyze_gate_balance(record)
        assert report.archetype is template.archetype
        assert report.budget.net_budget == template.net_budget


def test_templates_exercise_the_complete_existing_deterministic_surface() -> None:
    templates = load_gate_roster_templates(TEMPLATES)

    assert {template.prototype.target_mode for template in templates} == {0, 1, 2}
    assert {template.prototype.effect_id for template in templates} == {1, 2}
    assert {template.prototype.condition_id for template in templates} == set(range(8))
    assert {template.prototype.preferred_type for template in templates} == set(range(6))

    for archetype in LIVE_ARCHETYPES:
        variants = [
            template for template in templates if template.archetype is archetype
        ]
        assert len(
            {
                (item.prototype.flat_bonus_g, item.prototype.percent_q8_8)
                for item in variants
            }
        ) >= 2
        assert len({item.prototype.attribute_modifiers for item in variants}) >= 2
        assert len({item.prototype.battle_weights for item in variants}) >= 2
        assert len({item.prototype.condition_id for item in variants}) >= 2

    for template in templates:
        if template.archetype in (GateArchetype.RISK, GateArchetype.CHAOS):
            assert template.prototype.drawback_id != 0
            assert template.prototype.drawback_value != 0


def test_template_parser_rejects_legacy_duplicates_unsupported_state_and_bad_order() -> None:
    payload = _payload()

    legacy = json.loads(json.dumps(payload))
    legacy["templates"][0]["archetype"] = 0
    with pytest.raises(WorkspaceError, match="live archetype"):
        parse_gate_roster_templates(legacy)

    duplicate_id = json.loads(json.dumps(payload))
    duplicate_id["templates"][1]["template_id"] = duplicate_id["templates"][0][
        "template_id"
    ]
    with pytest.raises(WorkspaceError, match="duplicate Gate roster template ID"):
        parse_gate_roster_templates(duplicate_id)

    duplicate_runtime = json.loads(json.dumps(payload))
    duplicate_runtime["templates"][1]["record"] = duplicate_runtime["templates"][0][
        "record"
    ]
    duplicate_runtime["templates"][1]["archetype"] = duplicate_runtime[
        "templates"
    ][0]["archetype"]
    with pytest.raises(WorkspaceError, match="duplicate runtime signature"):
        parse_gate_roster_templates(duplicate_runtime)

    unsupported = json.loads(json.dumps(payload))
    unsupported["templates"][0]["record"]["activation_limit"] = 1
    with pytest.raises(WorkspaceError, match="deferred state fields"):
        parse_gate_roster_templates(unsupported)

    bad_order = json.loads(json.dumps(payload))
    bad_order["templates"][0], bad_order["templates"][1] = (
        bad_order["templates"][1],
        bad_order["templates"][0],
    )
    with pytest.raises(WorkspaceError, match="canonical archetype/template order"):
        parse_gate_roster_templates(bad_order)


def test_template_parser_rejects_incomplete_coverage_unknown_fields_and_bad_card_id() -> None:
    payload = _payload()

    incomplete = json.loads(json.dumps(payload))
    incomplete["templates"] = incomplete["templates"][1:]
    with pytest.raises(WorkspaceError, match="at least two templates"):
        parse_gate_roster_templates(incomplete)

    unknown = json.loads(json.dumps(payload))
    unknown["unexpected"] = True
    with pytest.raises(WorkspaceError, match="document fields mismatch"):
        parse_gate_roster_templates(unknown)

    entry_unknown = json.loads(json.dumps(payload))
    entry_unknown["templates"][0]["unexpected"] = True
    with pytest.raises(WorkspaceError, match="template fields mismatch"):
        parse_gate_roster_templates(entry_unknown)

    templates = load_gate_roster_templates(TEMPLATES)
    with pytest.raises(WorkspaceError, match="card ID must be between 1 and 103"):
        templates[0].instantiate(card_id=0)


def test_template_writer_is_deterministic(tmp_path: Path) -> None:
    templates = load_gate_roster_templates(TEMPLATES)
    output = tmp_path / "templates.json"

    write_gate_roster_templates(output, templates)
    first = output.read_bytes()
    write_gate_roster_templates(output, templates)

    assert output.read_bytes() == first
    assert first.endswith(b"\n")
    assert load_gate_roster_templates(output) == templates
    assert all(isinstance(template, GateRosterTemplate) for template in templates)
