import os
from pathlib import Path

import pytest

from bakugan_ds.profile import RomProfile, load_profile
from bakugan_ds.workspace.extract import ExtractionOptions, extract_workspace
from bakugan_ds.workspace.manifest import WorkspaceManifest


@pytest.fixture(scope="session")
def reference_rom() -> Path:
    value = os.environ.get("BAKUGAN_DS_ROM")
    if value is None:
        pytest.skip("set BAKUGAN_DS_ROM to run reference-ROM integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"BAKUGAN_DS_ROM does not point to a file: {path}")
    return path


@pytest.fixture(scope="session")
def reference_runtime_arm9() -> Path:
    value = os.environ.get("BAKUGAN_DS_RUNTIME_ARM9")
    if value is None:
        pytest.skip("set BAKUGAN_DS_RUNTIME_ARM9 to run runtime ARM9 integration tests")
    path = Path(value)
    if not path.is_file():
        pytest.fail(f"BAKUGAN_DS_RUNTIME_ARM9 does not point to a file: {path}")
    return path


@pytest.fixture(scope="session")
def reference_profile() -> RomProfile:
    return load_profile(Path("config/b6re_rev0.json"))


@pytest.fixture(scope="session")
def reference_workspace(
    reference_rom: Path,
    reference_profile: RomProfile,
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, WorkspaceManifest]:
    workspace = tmp_path_factory.mktemp("reference-workspace") / "workspace"
    manifest = extract_workspace(reference_rom, reference_profile, ExtractionOptions(workspace))
    return workspace, manifest
