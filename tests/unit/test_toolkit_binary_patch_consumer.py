import json
from pathlib import Path

import pytest
from nds_disassembly_toolkit.patches.apply import AppliedPatch as ToolkitAppliedPatch
from nds_disassembly_toolkit.patches.apply import (
    PatchApplicationReport as ToolkitPatchApplicationReport,
)
from nds_disassembly_toolkit.patches.model import BinaryPatch as ToolkitBinaryPatch
from nds_disassembly_toolkit.patches.model import PatchSet as ToolkitPatchSet

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.patches.apply import AppliedPatch, PatchApplicationReport
from bakugan_ds.patches.model import BinaryPatch, PatchSet, load_patch_set


def test_binary_patch_types_are_toolkit_owned() -> None:
    assert BinaryPatch is ToolkitBinaryPatch
    assert PatchSet is ToolkitPatchSet
    assert AppliedPatch is ToolkitAppliedPatch
    assert PatchApplicationReport is ToolkitPatchApplicationReport


def test_bakugan_patch_set_requires_profile_id(tmp_path: Path) -> None:
    path = tmp_path / "patch.json"
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "profile_id": None,
                "patches": [
                    {
                        "id": "test",
                        "type": "binary_replace",
                        "target": "arm9",
                        "offset": 0,
                        "expected": "00",
                        "replacement": "11",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceError, match="missing profile_id"):
        load_patch_set(path)
