from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from bakugan_ds.gates import cli as gate_cli
from bakugan_ds.gates.readiness_report import generate_readiness_report
from bakugan_ds.gates.record import GateRecordV1, build_trailer


def _field(
    name: str,
    *,
    confidence: str = "confirmed",
    presence: str = "present",
    allowed_exception: bool = False,
) -> dict[str, object]:
    present = presence == "present"
    return {
        "access": "+0x00" if present else "unresolved",
        "allowed_exception": allowed_exception,
        "confidence": confidence,
        "evidence": "controlled evidence",
        "initialization": "constructor" if present else "unresolved",
        "lifetime": "match",
        "mutations": ["documented" if present else "unresolved"],
        "name": name,
        "owner_structure": "object" if present else "unresolved",
        "player_ai_behavior": "shared" if present else "unresolved",
        "presence": presence,
        "replacement_plan": "",
        "reset": "match reset" if present else "unresolved",
        "scripted_behavior": "documented" if present else "unresolved",
        "signed": False if present else None,
        "width_bits": 8 if present else None,
    }


def _write_artifact(
    path: Path,
    domain: str,
    field: dict[str, object],
) -> None:
    unresolved = [field["name"]] if field["presence"] == "deferred" else []
    path.write_text(
        json.dumps(
            {
                "checks": [],
                "domain": domain,
                "fields": [field],
                "format_version": 1,
                "unresolved": unresolved,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_requirements(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "requirements": [
                    {
                        "allow_absent": False,
                        "allow_deferred": False,
                        "artifact": "ownership",
                        "field": "gate_owner",
                        "name": "gate_owner",
                    },
                    {
                        "allow_absent": False,
                        "allow_deferred": True,
                        "artifact": "landing",
                        "field": "arena_id",
                        "name": "arena_id",
                    },
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _record(card_id: int) -> GateRecordV1:
    return GateRecordV1(
        card_id=card_id,
        archetype=0,
        flags=0,
        flat_bonus_g=0,
        percent_q8_8=0,
        attribute_modifiers=(0, 0, 0, 0, 0, 0),
        battle_weights=(0, 0, 0, 0, 0, 0),
        preferred_type=255,
        condition_id=0,
        effect_id=0,
        drawback_id=0,
        effect_value=0,
        drawback_value=0,
        activation_limit=0,
        fatigue_rate=0,
        target_mode=0,
        timing_phase=0,
        condition_value=0,
        secondary_effect_id=0,
        secondary_condition_id=0,
        secondary_value=0,
        reserved=0,
    )


def test_gate_parser_defines_validation_and_readiness_commands() -> None:
    parser = gate_cli.build_gate_parser()
    cases = (
        ("validate-artifact", ["validate-artifact", "artifact.json"]),
        ("validate-trailer", ["validate-trailer", "trailer.bin"]),
        (
            "readiness",
            [
                "readiness",
                "--requirements",
                "requirements.json",
                "--evidence-dir",
                "analysis/gates",
                "--output",
                "report.json",
            ],
        ),
    )
    for expected, arguments in cases:
        assert parser.parse_args(arguments).gate_command == expected


def test_validate_artifact_command_prints_normalized_summary(capsys) -> None:
    arguments = Namespace(
        gate_command="validate-artifact",
        artifact=Path("analysis/gates/system2-record-v1.json"),
    )
    assert gate_cli.run_gate_command(arguments) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["domain"] == "system2-record-v1"
    assert payload["valid"] is True
    assert "gate_record_geometry" in payload["fields"]


def test_validate_trailer_command_prints_exact_geometry(
    tmp_path: Path,
    capsys,
) -> None:
    trailer = tmp_path / "gates.bin"
    trailer.write_bytes(
        build_trailer(tuple(_record(card_id) for card_id in range(1, 104)))
    )
    arguments = Namespace(gate_command="validate-trailer", trailer=trailer)
    assert gate_cli.run_gate_command(arguments) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["header_size"] == 32
    assert payload["record_size"] == 40
    assert payload["record_count"] == 103
    assert payload["valid"] is True


def test_readiness_command_returns_four_for_probable_required_field(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    requirements = tmp_path / "requirements.json"
    output = tmp_path / "report.json"
    _write_requirements(requirements)
    _write_artifact(
        evidence / "ownership.json",
        "ownership",
        _field("gate_owner", confidence="probable"),
    )
    _write_artifact(
        evidence / "landing.json",
        "landing",
        _field(
            "arena_id",
            confidence="candidate",
            presence="deferred",
            allowed_exception=True,
        ),
    )
    arguments = Namespace(
        gate_command="readiness",
        requirements=requirements,
        evidence_dir=evidence,
        output=output,
    )
    assert gate_cli.run_gate_command(arguments) == 4
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ready_for_milestone_6c"] is False
    assert any(
        failure["requirement"] == "gate_owner"
        for failure in payload["failures"]
    )


def test_readiness_report_is_deterministic_and_ready_only_with_arena_deferred(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    requirements = tmp_path / "requirements.json"
    _write_requirements(requirements)
    _write_artifact(
        evidence / "ownership.json",
        "ownership",
        _field("gate_owner"),
    )
    _write_artifact(
        evidence / "landing.json",
        "landing",
        _field(
            "arena_id",
            confidence="probable",
            presence="deferred",
            allowed_exception=True,
        ),
    )
    first = generate_readiness_report(requirements, evidence)
    second = generate_readiness_report(requirements, evidence)
    assert first == second
    assert first.ready_for_milestone_6c is True
    assert first.confirmed == ("gate_owner",)
    assert first.deferred == ("arena_id",)
    assert first.failures == ()
    assert tuple(first.artifact_hashes) == ("landing", "ownership")


def test_readiness_report_rejects_duplicate_required_domain(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    requirements = tmp_path / "requirements.json"
    _write_requirements(requirements)
    _write_artifact(
        evidence / "ownership-a.json",
        "ownership",
        _field("gate_owner"),
    )
    _write_artifact(
        evidence / "ownership-b.json",
        "ownership",
        _field("gate_owner"),
    )
    _write_artifact(
        evidence / "landing.json",
        "landing",
        _field(
            "arena_id",
            confidence="probable",
            presence="deferred",
            allowed_exception=True,
        ),
    )
    report = generate_readiness_report(requirements, evidence)
    assert report.ready_for_milestone_6c is False
    assert any(
        failure.requirement == "artifact:ownership"
        for failure in report.failures
    )
