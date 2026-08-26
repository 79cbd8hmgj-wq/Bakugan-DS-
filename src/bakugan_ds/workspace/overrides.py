from pathlib import Path

from nds_disassembly_toolkit.workspace.overrides import (
    BuildOverrides as ToolkitBuildOverrides,
    OverlayLayoutOverride,
    RawNitroFsOverride,
    load_build_overrides as _toolkit_load_build_overrides,
    write_build_overrides as _toolkit_write_build_overrides,
)

from bakugan_ds.errors import WorkspaceError

SUPPORTED_PROFILE_ID = "b6re_rev0"


class BuildOverrides(ToolkitBuildOverrides):
    def validate(self) -> None:
        super().validate()
        if self.profile_id != SUPPORTED_PROFILE_ID:
            raise WorkspaceError(f"unsupported build override profile: {self.profile_id}")


def load_build_overrides(path: Path) -> BuildOverrides | None:
    loaded = _toolkit_load_build_overrides(path)
    if loaded is None:
        return None
    result = BuildOverrides(
        loaded.format_version,
        loaded.profile_id,
        loaded.raw_nitrofs,
        loaded.overlays,
    )
    result.validate()
    return result


def write_build_overrides(path: Path, overrides: BuildOverrides) -> None:
    overrides.validate()
    _toolkit_write_build_overrides(path, overrides)


__all__ = [
    "SUPPORTED_PROFILE_ID",
    "BuildOverrides",
    "OverlayLayoutOverride",
    "RawNitroFsOverride",
    "load_build_overrides",
    "write_build_overrides",
]
