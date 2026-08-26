from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.source_compile import (
    SourceToolchain,
    build_compile_command,
    build_link_command,
    build_linker_script,
    compile_source_patch,
    parse_nm_symbols,
)
from bakugan_ds.source_patch import load_source_patch_manifest


def _manifest_payload() -> dict[str, object]:
    return {
        "format_version": 1,
        "profile_id": "b6re_rev0",
        "target": "overlay:7",
        "runtime_address": 0x0221A000,
        "max_size": 0x100,
        "mode": "arm",
        "expected_runtime_sha256": hashlib.sha256(b"target").hexdigest(),
        "sources": ["src/injected.c"],
        "definitions": {
            "known_helper": 0x02065BF4,
            "other_helper": 0x02000010,
        },
        "hooks": [],
    }


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    manifest_path = tmp_path / "source-patch.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return manifest_path


def test_build_compile_command_is_explicit_armv5te() -> None:
    toolchain = SourceToolchain(clang="clang-custom", ld="ld.lld", nm="nm")

    command = build_compile_command(
        toolchain,
        Path("src/injected.c"),
        Path("build/injected.o"),
        mode="arm",
    )

    assert command == (
        "clang-custom",
        "--target=arm-none-eabi",
        "-mcpu=arm946e-s",
        "-marm",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-fno-unwind-tables",
        "-fno-asynchronous-unwind-tables",
        "-c",
        "src/injected.c",
        "-o",
        "build/injected.o",
    )


def test_build_compile_command_switches_to_thumb() -> None:
    command = build_compile_command(
        SourceToolchain(),
        Path("entry.s"),
        Path("entry.o"),
        mode="thumb",
    )

    assert "-mthumb" in command
    assert "-marm" not in command


def test_linker_script_binds_exact_approved_range_and_forbids_bss() -> None:
    script = build_linker_script(0x0221A000, 0x100)

    assert ". = 0x0221A000;" in script
    assert 'ASSERT(SIZEOF(.bss) == 0, "BSS forbidden")' in script
    assert 'ASSERT(. <= 0x0221A100, "source patch exceeds approved byte budget")' in script
    assert "*(.ARM.exidx*)" in script
    assert "*(.ARM.extab*)" in script


def test_build_link_command_sorts_definitions_and_supports_binary() -> None:
    command = build_link_command(
        SourceToolchain(ld="lld-custom"),
        objects=(Path("b.o"), Path("a.o")),
        linker_script=Path("link.ld"),
        output=Path("out.bin"),
        definitions=(("zeta", 0x30), ("alpha", 0x20)),
        binary=True,
    )

    assert command == (
        "lld-custom",
        "--entry=0",
        "-T",
        "link.ld",
        "--defsym=alpha=0x00000020",
        "--defsym=zeta=0x00000030",
        "a.o",
        "b.o",
        "--oformat=binary",
        "-o",
        "out.bin",
    )


def test_parse_nm_symbols_is_deterministic() -> None:
    symbols = parse_nm_symbols(
        "0221a010 T second\n"
        "0221a000 T entry\n"
        "02065bf4 A known_helper\n"
    )

    assert symbols == (
        ("known_helper", 0x02065BF4),
        ("entry", 0x0221A000),
        ("second", 0x0221A010),
    )


def test_parse_nm_symbols_rejects_duplicate_names() -> None:
    with pytest.raises(WorkspaceError, match="duplicate symbol"):
        parse_nm_symbols("0221a000 T entry\n0221a004 T entry\n")


def test_compile_source_patch_runs_tools_without_shell_and_returns_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_manifest(tmp_path, _manifest_payload())
    source = tmp_path / "src" / "injected.c"
    source.parent.mkdir(parents=True)
    source.write_text("int entry(int x) { return x + 1; }\n", encoding="utf-8")
    manifest = load_source_patch_manifest(manifest_path)
    calls: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...]) -> str:
        calls.append(command)
        if command[0] == "clang":
            Path(command[command.index("-o") + 1]).write_bytes(b"object")
            return ""
        if command[0] == "ld.lld":
            output = Path(command[command.index("-o") + 1])
            if "--oformat=binary" in command:
                output.write_bytes(bytes.fromhex("0100a0e3"))
            else:
                output.write_bytes(b"elf")
            return ""
        if command[0] == "nm":
            return "0221a000 T entry\n02065bf4 A known_helper\n"
        raise AssertionError(command)

    monkeypatch.setattr("bakugan_ds.source_compile.run_command", fake_run)

    result = compile_source_patch(
        manifest_path,
        manifest,
        SourceToolchain(),
        runner=fake_run,
    )

    assert result.image == bytes.fromhex("0100a0e3")
    assert result.symbols == (
        ("known_helper", 0x02065BF4),
        ("entry", 0x0221A000),
    )
    assert result.source_hashes == (
        ("src/injected.c", hashlib.sha256(source.read_bytes()).hexdigest()),
    )
    assert len(result.commands) == 4
    assert all(isinstance(command, tuple) for command in result.commands)


def test_compile_source_patch_rejects_missing_source(tmp_path: Path) -> None:
    manifest_path = _write_manifest(tmp_path, _manifest_payload())
    manifest = load_source_patch_manifest(manifest_path)

    with pytest.raises(WorkspaceError, match="source file"):
        compile_source_patch(manifest_path, manifest, SourceToolchain())


def test_compile_source_patch_rejects_oversized_binary(
    tmp_path: Path,
) -> None:
    payload = _manifest_payload()
    payload["max_size"] = 4
    manifest_path = _write_manifest(tmp_path, payload)
    source = tmp_path / "src" / "injected.c"
    source.parent.mkdir(parents=True)
    source.write_text("void entry(void) {}\n", encoding="utf-8")
    manifest = load_source_patch_manifest(manifest_path)

    def fake_run(command: tuple[str, ...]) -> str:
        if command[0] == "clang":
            Path(command[command.index("-o") + 1]).write_bytes(b"object")
        elif command[0] == "ld.lld":
            output = Path(command[command.index("-o") + 1])
            output.write_bytes(b"12345" if "--oformat=binary" in command else b"elf")
        elif command[0] == "nm":
            return "0221a000 T entry\n"
        return ""

    with pytest.raises(WorkspaceError, match="exceeds max_size"):
        compile_source_patch(
            manifest_path,
            manifest,
            SourceToolchain(),
            runner=fake_run,
        )
