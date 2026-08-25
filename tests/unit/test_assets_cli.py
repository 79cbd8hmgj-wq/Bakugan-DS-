from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds import assets_cli, cli


def test_assets_inventory_dispatches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = []
    monkeypatch.setattr(cli, "run_assets_command", lambda args: calls.append(args) or 0)

    result = cli.main(
        [
            "assets",
            "inventory",
            str(tmp_path / "game.nds"),
            "--include-unknown",
            "--allow-unsupported",
        ]
    )

    assert result == 0
    assert calls[0].assets_command == "inventory"
    assert calls[0].include_unknown is True
    assert calls[0].allow_unsupported is True


def test_assets_inventory_writes_deterministic_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rom_path = tmp_path / "game.nds"
    rom_path.write_bytes(b"rom")
    output = tmp_path / "assets.json"

    class FakeInventory:
        def to_json(self) -> str:
            return '{"format_version": 1}\n'

    monkeypatch.setattr(assets_cli, "load_profile", lambda path: object())
    monkeypatch.setattr(
        assets_cli,
        "inspect_rom",
        lambda path, profile, require_supported: object(),
    )
    monkeypatch.setattr(
        assets_cli,
        "inventory_assets",
        lambda data, inspection, include_unknown: FakeInventory(),
    )

    parser = cli.build_parser()
    arguments = parser.parse_args(
        [
            "assets",
            "inventory",
            str(rom_path),
            "--output",
            str(output),
        ]
    )
    result = assets_cli.run_assets_command(arguments)

    assert result == 0
    assert output.read_text(encoding="utf-8") == '{"format_version": 1}\n'
