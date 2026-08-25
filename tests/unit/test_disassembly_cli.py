from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from bakugan_ds import cli


def test_disasm_module_params_outputs_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    binary = tmp_path / "arm9.bin"
    binary.write_bytes(
        b"\x00" * 0x20
        + struct.pack(
            "<8I",
            0x020C0100,
            0x020C0118,
            0x020BAF00,
            0x020BAF00,
            0x02219440,
            0x0206D6C0,
            0x04027539,
            0xDEC00621,
        )
    )

    result = cli.main(
        [
            "disasm",
            "module-params",
            str(binary),
            "--base-address",
            "0x02000000",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["offset"] == 0x20
    assert payload["address"] == 0x02000020
    assert payload["static_bss_end"] == 0x02219440


def test_disasm_labels_writes_labelled_byte_file(tmp_path: Path) -> None:
    binary = tmp_path / "component.bin"
    offsets = tmp_path / "labels.txt"
    output = tmp_path / "component.s"
    binary.write_bytes(bytes(range(8)))
    offsets.write_text("0x02000004\n", encoding="utf-8")

    result = cli.main(
        [
            "disasm",
            "labels",
            str(binary),
            str(offsets),
            "--vma",
            "0x02000000",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    text = output.read_text(encoding="utf-8")
    assert text.startswith("_02000000:\n")
    assert "_02000004:\n" in text


def test_disasm_overlay_map_dispatches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []
    monkeypatch.setattr(cli, "run_disassembly_command", lambda args: calls.append(args) or 0)

    result = cli.main(["disasm", "overlay-map", str(tmp_path / "game.nds")])

    assert result == 0
    assert calls[0].disasm_command == "overlay-map"


def test_disasm_diff_dispatches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = []
    monkeypatch.setattr(cli, "run_disassembly_command", lambda args: calls.append(args) or 0)

    result = cli.main(
        [
            "disasm",
            "diff",
            str(tmp_path / "original.bin"),
            str(tmp_path / "rebuilt.bin"),
            "--vma",
            "0x02219440",
        ]
    )

    assert result == 0
    assert calls[0].disasm_command == "diff"
