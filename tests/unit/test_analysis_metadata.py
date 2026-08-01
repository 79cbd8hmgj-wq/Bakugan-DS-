from pathlib import Path


def test_memory_map_contains_verified_addresses() -> None:
    text = Path("analysis/memory-map.yaml").read_text(encoding="utf-8")
    for required in (
        "game_code: B6RE",
        "arm9_ram_address: 0x02000000",
        "arm7_ram_address: 0x02380000",
        "fnt_offset: 0x000FFC00",
        "arm9_overlay_table_offset: 0x00071800",
        "overlay_load_address: 0x02219440",
        "confidence: confirmed",
    ):
        assert required in text


def test_overlay_metadata_records_all_nine_ids() -> None:
    text = Path("analysis/overlays.yaml").read_text(encoding="utf-8")
    for overlay_id in range(9):
        assert f"- overlay_id: {overlay_id}\n" in text
    assert "overlay_id: 7" in text
    assert "ram_address: 0x02219440" in text
    assert "ram_size: 467360" in text
    assert "bss_size: 1600" in text
    assert "compressed_size: 255740" in text


def test_reverse_engineering_workflow_defines_confidence_levels() -> None:
    text = Path("docs/reverse-engineering-workflow.md").read_text(encoding="utf-8")
    assert "## Confirmed" in text
    assert "## Probable" in text
    assert "## Candidate" in text
    assert "runtime address" in text
    assert "component-relative offset" in text
