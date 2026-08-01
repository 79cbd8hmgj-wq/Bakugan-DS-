from pathlib import Path

WORKFLOW = Path(".github/workflows/build-desmume-debug.yml")


def test_desmume_workflow_is_manual_and_read_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "permissions:\n  contents: read" in text


def test_desmume_workflow_pins_and_verifies_debug_build() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for required in (
        "84e445159ccf2fd7900748094518eb1e88bdc7d0",
        "ubuntu-24.04",
        "--enable-gdb-stub",
        "desmume-cli",
        "arm9gdb",
        "ldd",
        "SHA256SUMS",
        "retention-days: 7",
        "if-no-files-found: error",
    ):
        assert required in text


def test_desmume_workflow_never_handles_game_data() -> None:
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    for forbidden in ("*.nds", "*.sav", "*.dsv", "save state", "bakugan - battle brawlers"):
        assert forbidden not in text
