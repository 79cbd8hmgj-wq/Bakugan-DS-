import csv
import json
from pathlib import Path


OBSERVATION = Path("analysis/runtime-observations/persistent_gpower_storage.json")
SYMBOLS = Path("analysis/symbols/persistent_gpower.csv")
DOCUMENT = Path("docs/persistent-gpower-storage.md")


def load_observation() -> dict[str, object]:
    return json.loads(OBSERVATION.read_text(encoding="utf-8"))


def test_persistent_table_geometry_and_scaling() -> None:
    payload = load_observation()
    table = payload["persistent_player_gpower"]
    assert table["global_roster_base"] == "0x020D43F0"
    assert table["table_offset"] == "0x0460"
    assert table["table_address"] == "0x020D4850"
    assert table["bakugan_identity_count"] == 41
    assert table["attribute_count"] == 6
    assert table["entry_count"] == 41 * 6 == 246
    assert table["entry_size_bytes"] == 1
    assert table["stored_unit_g"] == 10
    assert table["index_formula"] == (
        "owner_bank * 246 + bakugan_id * 6 + attribute_id"
    )
    assert table["value_formula"] == "current_g = stored_byte * 10"


def test_runtime_helpers_are_exact_and_do_not_use_old_bad_addresses() -> None:
    payload = load_observation()
    helpers = {item["name"]: item for item in payload["confirmed_helpers"]}
    assert helpers["PlayerGPower_IdentityIndex"]["address"] == "0x0202317C"
    assert helpers["PlayerGPower_SetStored"]["address"] == "0x020231C0"
    assert helpers["PlayerGPower_GetStored"]["address"] == "0x020231F4"
    assert helpers["PlayerBakuganAux_GetRecord"]["address"] == "0x02023248"
    serialized = json.dumps(payload)
    assert "0x02009C" not in serialized
    assert "0x02009D" not in serialized
    assert "0x02009E" not in serialized


def test_fd_is_rejected_as_persistent_progression() -> None:
    payload = load_observation()
    field = payload["battle_counter_fd"]
    assert field["participant_offset"] == "0x00FD"
    assert field["confidence"] == "confirmed_nonpersistent_battle_state"
    rejected = set(field["rejected_interpretations"])
    assert rejected == {
        "persistent level",
        "persistent experience",
        "persistent roster progression",
    }
    evidence = {item["address"]: item["behavior"] for item in field["evidence"]}
    assert evidence["0x02234D28"].startswith("initialized to zero")
    assert evidence["0x02269700"].startswith("initialized to zero")
    assert "incremented" in evidence["0x0222D158"]
    assert "battle-results" in evidence["0x022502F8"]
    assert "cleared" in evidence["0x02235718"]


def test_normal_level_up_writer_remains_unresolved() -> None:
    payload = load_observation()
    boundaries = payload["confidence_boundaries"]
    assert boundaries["normal_level_up_commit_path"] == "unresolved"
    assert boundaries["evolution_storage_model"] == "candidate"
    callsites = payload["direct_setter_callsites"]
    assert all("level-up" not in item["role"].lower() for item in callsites)


def test_symbol_catalog_and_document_match_the_evidence_boundary() -> None:
    with SYMBOLS.open(newline="", encoding="utf-8") as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)}
    assert rows["PlayerGPower_Table"]["address"] == "0x020D4850"
    assert rows["PlayerGPower_GetStored"]["confidence"] == "confirmed"
    assert rows["BattleParticipant_ResultCounterFD"]["confidence"] == (
        "confirmed_nonpersistent"
    )

    text = DOCUMENT.read_text(encoding="utf-8")
    for required in (
        "41 × 6",
        "0x020D4850",
        "current_g = table[index] * 10",
        "must not be used",
        "is not level or experience",
        "normal level-up",
        "No gameplay patch is included",
    ):
        assert required in text
    assert "TODO" not in text
    assert "TBD" not in text
