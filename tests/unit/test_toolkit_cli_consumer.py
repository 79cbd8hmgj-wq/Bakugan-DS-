from __future__ import annotations

from bakugan_ds import assets_cli, cli, disassembly_cli, source_patch_cli
from nds_disassembly_toolkit import assets_cli as toolkit_assets_cli
from nds_disassembly_toolkit import disassembly_cli as toolkit_disassembly_cli
from nds_disassembly_toolkit import source_patch_cli as toolkit_source_patch_cli


def test_generic_cli_runners_are_toolkit_owned() -> None:
    assert assets_cli.run_assets_command is toolkit_assets_cli.run_assets_command
    assert disassembly_cli.run_disassembly_command is toolkit_disassembly_cli.run_disassembly_command


def test_bakugan_cli_keeps_supported_rom_policy() -> None:
    parser = cli.build_parser()

    assets = parser.parse_args(["assets", "inventory", "game.nds"])
    assert assets.profile == cli.DEFAULT_PROFILE
    assert assets.require_supported is True

    assets_relaxed = parser.parse_args(
        ["assets", "inventory", "game.nds", "--allow-unsupported"]
    )
    assert assets_relaxed.require_supported is False

    overlay = parser.parse_args(["disasm", "overlay-map", "game.nds"])
    assert overlay.profile == cli.DEFAULT_PROFILE
    assert overlay.require_supported is True

    overlay_relaxed = parser.parse_args(
        ["disasm", "overlay-map", "game.nds", "--allow-unsupported"]
    )
    assert overlay_relaxed.require_supported is False


def test_source_patch_runner_remains_bakugan_policy_adapter() -> None:
    assert source_patch_cli.run_source_patch_command is not toolkit_source_patch_cli.run_source_patch_command

    parser = cli.build_parser()
    arguments = parser.parse_args(["source-patch", "build", "workspace", "patch.json"])
    assert arguments.profile == cli.DEFAULT_PROFILE
