from __future__ import annotations

import pytest

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.identity import (
    AttributeIdentity,
    GateIdentityMapping,
    attribute_order_from_messages,
    normalize_identity_capture,
    parse_indexed_messages,
)


def encode_message(text: str) -> bytes:
    encoded = bytearray()
    for character in text:
        if character == " ":
            encoded += (0xFF84).to_bytes(2, "little")
        else:
            encoded += (ord(character) - 0x20).to_bytes(2, "little")
    encoded += (0xFF80).to_bytes(2, "little")
    return bytes(encoded)


def make_catalog(messages: list[str]) -> bytes:
    header_size = 2 + len(messages) * 4
    payload = bytearray(header_size)
    payload[:2] = len(messages).to_bytes(2, "little")
    cursor = header_size
    for index, message in enumerate(messages):
        encoded = encode_message(message)
        payload[2 + index * 4 : 4 + index * 4] = cursor.to_bytes(2, "little")
        payload[4 + index * 4 : 6 + index * 4] = len(encoded).to_bytes(2, "little")
        payload.extend(encoded)
        cursor += len(encoded)
    return bytes(payload)


def test_identity_capture_keeps_numeric_id_canonical() -> None:
    attributes, mappings = normalize_identity_capture(
        {
            "attributes": [
                {
                    "attribute_id": 0,
                    "name": "Pyrus",
                    "confidence": "confirmed",
                    "evidence_id": "attr-0",
                }
            ],
            "mappings": [
                {
                    "card_id": 22,
                    "label": "Serpenoid",
                    "runtime_case": "message-index-22",
                    "confidence": "confirmed",
                    "evidence_id": "card-22",
                }
            ],
        }
    )

    assert attributes == (AttributeIdentity(0, "Pyrus", "confirmed", "attr-0"),)
    assert mappings == (
        GateIdentityMapping(22, "Serpenoid", "message-index-22", "confirmed", "card-22"),
    )


def test_identity_capture_rejects_duplicate_ids() -> None:
    payload = {
        "attributes": [
            {
                "attribute_id": 0,
                "name": "Pyrus",
                "confidence": "confirmed",
                "evidence_id": "a",
            },
            {
                "attribute_id": 0,
                "name": "Aquos",
                "confidence": "confirmed",
                "evidence_id": "b",
            },
        ],
        "mappings": [],
    }
    with pytest.raises(WorkspaceError, match="duplicate attribute ID"):
        normalize_identity_capture(payload)


def test_indexed_message_parser_preserves_entry_index() -> None:
    messages = parse_indexed_messages(make_catalog(["-", "Juggernoid", "Serpenoid"]))
    assert messages == ("-", "Juggernoid", "Serpenoid")


def test_attribute_order_comes_from_first_six_game_messages() -> None:
    messages = (
        "Pyrus Bakugan have a battle advantage.",
        "Aquos Bakugan have a battle advantage.",
        "Subterra Bakugan have a battle advantage.",
        "Haos Bakugan have a battle advantage.",
        "Darkus Bakugan have a battle advantage.",
        "Ventus Bakugan have a battle advantage.",
    )
    assert attribute_order_from_messages(messages) == (
        "pyrus",
        "aquos",
        "subterra",
        "haos",
        "darkus",
        "ventus",
    )


def test_message_parser_rejects_out_of_bounds_entry() -> None:
    malformed = bytearray(make_catalog(["Serpenoid"]))
    malformed[2:4] = (0xFFFF).to_bytes(2, "little")
    with pytest.raises(WorkspaceError, match="outside message catalog"):
        parse_indexed_messages(bytes(malformed))
