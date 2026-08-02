from __future__ import annotations

from dataclasses import dataclass

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence

ATTRIBUTE_NAMES = ("pyrus", "aquos", "subterra", "haos", "darkus", "ventus")


@dataclass(frozen=True)
class AttributeIdentity:
    attribute_id: int
    name: str
    confidence: Confidence
    evidence_id: str

    def validate(self) -> None:
        if not 0 <= self.attribute_id < 6:
            raise WorkspaceError(f"attribute ID must be between 0 and 5, got {self.attribute_id}")
        if not self.name.strip():
            raise WorkspaceError("attribute name must be nonempty")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("attribute confidence is invalid")
        if not self.evidence_id.strip():
            raise WorkspaceError("attribute evidence ID must be nonempty")


@dataclass(frozen=True)
class GateIdentityMapping:
    card_id: int
    label: str
    runtime_case: str
    confidence: Confidence
    evidence_id: str

    def validate(self) -> None:
        if self.card_id < 0:
            raise WorkspaceError("card ID must be nonnegative")
        if not self.label.strip():
            raise WorkspaceError("Gate label must be nonempty")
        if not self.runtime_case.strip():
            raise WorkspaceError("Gate runtime case must be nonempty")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("Gate confidence is invalid")
        if not self.evidence_id.strip():
            raise WorkspaceError("Gate evidence ID must be nonempty")


def _require_array(payload: dict[str, object], name: str) -> list[object]:
    value = payload.get(name)
    if not isinstance(value, list):
        raise WorkspaceError(f"{name} must be a JSON array")
    return value


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def normalize_identity_capture(
    payload: dict[str, object],
) -> tuple[tuple[AttributeIdentity, ...], tuple[GateIdentityMapping, ...]]:
    attributes: list[AttributeIdentity] = []
    attribute_ids: set[int] = set()
    for index, raw in enumerate(_require_array(payload, "attributes")):
        item = _require_object(raw, f"attributes[{index}]")
        try:
            identity = AttributeIdentity(
                attribute_id=int(item["attribute_id"]),
                name=str(item["name"]),
                confidence=Confidence(str(item["confidence"])),
                evidence_id=str(item["evidence_id"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid attributes[{index}]: {exc}") from exc
        identity.validate()
        if identity.attribute_id in attribute_ids:
            raise WorkspaceError(f"duplicate attribute ID: {identity.attribute_id}")
        attribute_ids.add(identity.attribute_id)
        attributes.append(identity)

    mappings: list[GateIdentityMapping] = []
    card_ids: set[int] = set()
    for index, raw in enumerate(_require_array(payload, "mappings")):
        item = _require_object(raw, f"mappings[{index}]")
        try:
            mapping = GateIdentityMapping(
                card_id=int(item["card_id"]),
                label=str(item["label"]),
                runtime_case=str(item["runtime_case"]),
                confidence=Confidence(str(item["confidence"])),
                evidence_id=str(item["evidence_id"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid mappings[{index}]: {exc}") from exc
        mapping.validate()
        if mapping.card_id in card_ids:
            raise WorkspaceError(f"duplicate card ID: {mapping.card_id}")
        card_ids.add(mapping.card_id)
        mappings.append(mapping)

    return (
        tuple(sorted(attributes, key=lambda item: item.attribute_id)),
        tuple(sorted(mappings, key=lambda item: item.card_id)),
    )


def _decode_message_units(data: bytes) -> str:
    if len(data) % 2:
        raise WorkspaceError("message payload length must be even")
    characters: list[str] = []
    for offset in range(0, len(data), 2):
        value = int.from_bytes(data[offset : offset + 2], "little")
        if value in {0, 0xFF80}:
            continue
        if value == 0xFF84:
            characters.append(" ")
            continue
        if 1 <= value <= 0x5E:
            characters.append(chr(value + 0x20))
            continue
        raise WorkspaceError(f"unsupported message code 0x{value:04X}")
    return "".join(characters)


def parse_indexed_messages(data: bytes) -> tuple[str, ...]:
    if len(data) < 2:
        raise WorkspaceError("message catalog is truncated")
    count = int.from_bytes(data[:2], "little")
    header_end = 2 + count * 4
    if header_end > len(data):
        raise WorkspaceError("message catalog index is truncated")
    messages: list[str] = []
    for index in range(count):
        entry = 2 + index * 4
        offset = int.from_bytes(data[entry : entry + 2], "little")
        length = int.from_bytes(data[entry + 2 : entry + 4], "little")
        end = offset + length
        if offset < header_end or end > len(data):
            raise WorkspaceError(f"message {index} is outside message catalog")
        messages.append(_decode_message_units(data[offset:end]))
    return tuple(messages)


def attribute_order_from_messages(messages: tuple[str, ...]) -> tuple[str, ...]:
    if len(messages) < 6:
        raise WorkspaceError("attribute message catalog must contain at least six entries")
    resolved = tuple(message.split(" ", 1)[0].strip().lower() for message in messages[:6])
    if resolved != ATTRIBUTE_NAMES:
        raise WorkspaceError(
            "attribute message order does not match Pyrus, Aquos, Subterra, Haos, Darkus, Ventus"
        )
    return resolved
