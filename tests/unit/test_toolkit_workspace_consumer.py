from nds_disassembly_toolkit.workspace import manifest as toolkit_manifest
from nds_disassembly_toolkit.workspace import model as toolkit_model
from nds_disassembly_toolkit.workspace import paths as toolkit_paths

from bakugan_ds.workspace import manifest as bakugan_manifest
from bakugan_ds.workspace import model as bakugan_model
from bakugan_ds.workspace import paths as bakugan_paths


def test_workspace_model_is_owned_by_toolkit() -> None:
    assert bakugan_model.WorkspaceLayout is toolkit_model.WorkspaceLayout


def test_workspace_paths_are_owned_by_toolkit() -> None:
    assert bakugan_paths.safe_relative_path is toolkit_paths.safe_relative_path
    assert bakugan_paths.ensure_unique_relative_paths is toolkit_paths.ensure_unique_relative_paths


def test_workspace_manifest_is_owned_by_toolkit() -> None:
    assert bakugan_manifest.ExtractedFile is toolkit_manifest.ExtractedFile
    assert bakugan_manifest.ExtractedOverlay is toolkit_manifest.ExtractedOverlay
    assert bakugan_manifest.WorkspaceManifest is toolkit_manifest.WorkspaceManifest
    assert bakugan_manifest.load_workspace_manifest is toolkit_manifest.load_workspace_manifest
    assert bakugan_manifest.sha256_bytes is toolkit_manifest.sha256_bytes
    assert bakugan_manifest.write_json_atomic is toolkit_manifest.write_json_atomic
