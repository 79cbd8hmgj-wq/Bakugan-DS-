from __future__ import annotations

from pathlib import Path

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.source_apply import _commit_target_and_report


def test_commit_rejects_target_changed_after_validation(tmp_path: Path) -> None:
    target = tmp_path / "target.bin"
    report = tmp_path / "report.json"
    original = b"original"
    target.write_bytes(b"concurrent-edit")

    with pytest.raises(WorkspaceError, match="changed during build"):
        _commit_target_and_report(
            target,
            b"patched",
            report,
            b"{}\n",
            original,
        )

    assert target.read_bytes() == b"concurrent-edit"
    assert not report.exists()
