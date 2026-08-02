from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import json
from pathlib import Path

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.gates.model import Confidence

_VALID_WIDTHS = frozenset({8, 16, 32})


class ContextLifetime(StrEnum):
    BATTLE = "battle"
    GATE = "gate"
    MATCH = "match"
    PERSISTENT = "persistent"


@dataclass(frozen=True)
class BattleContextField:
    name: str
    width_bits: int
    signed: bool
    owner_structure: str
    access: str
    lifetime: ContextLifetime
    initialization: str
    reset: str
    safe_for_hook: bool
    confidence: Confidence
    evidence: str
    exclusion_reason: str = ""

    def validate(self) -> None:
        if not self.name.strip():
            raise WorkspaceError("battle-context field name must be nonempty")
        if self.width_bits not in _VALID_WIDTHS:
            raise WorkspaceError("battle-context field width must be 8, 16, or 32 bits")
        if type(self.signed) is not bool:
            raise WorkspaceError("battle-context signed must be a boolean")
        if not self.owner_structure.strip():
            raise WorkspaceError("battle-context owner structure must be nonempty")
        if not self.access.strip():
            raise WorkspaceError("battle-context access must be nonempty")
        if not isinstance(self.lifetime, ContextLifetime):
            raise WorkspaceError("battle-context lifetime is invalid")
        if type(self.safe_for_hook) is not bool:
            raise WorkspaceError("battle-context safe_for_hook must be a boolean")
        if not isinstance(self.confidence, Confidence):
            raise WorkspaceError("battle-context confidence is invalid")
        if not self.evidence.strip():
            raise WorkspaceError("battle-context evidence must be nonempty")
        if self.confidence is not Confidence.CONFIRMED and not self.exclusion_reason.strip():
            raise WorkspaceError("unconfirmed battle-context field requires an exclusion reason")
        if self.safe_for_hook and self.confidence is not Confidence.CONFIRMED:
            raise WorkspaceError("only confirmed battle-context fields may be safe for hooks")

    @property
    def hook_ready(self) -> bool:
        return (
            self.confidence is Confidence.CONFIRMED
            and self.safe_for_hook
            and bool(self.initialization.strip())
            and bool(self.reset.strip())
        )


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be a JSON object")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise WorkspaceError(f"{label} must be a JSON array")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise WorkspaceError(f"{label} must be a boolean")
    return value


def load_context_fields(path: Path) -> tuple[BattleContextField, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load Gate battle context {path}: {exc}") from exc
    root = _require_object(payload, "battle-context document")
    fields: list[BattleContextField] = []
    names: set[str] = set()
    for index, raw in enumerate(_require_array(root.get("fields"), "fields")):
        item = _require_object(raw, f"fields[{index}]")
        try:
            field = BattleContextField(
                name=str(item["name"]),
                width_bits=int(item["width_bits"]),
                signed=_require_bool(item["signed"], f"fields[{index}].signed"),
                owner_structure=str(item["owner_structure"]),
                access=str(item["access"]),
                lifetime=ContextLifetime(str(item["lifetime"])),
                initialization=str(item["initialization"]),
                reset=str(item["reset"]),
                safe_for_hook=_require_bool(
                    item["safe_for_hook"], f"fields[{index}].safe_for_hook"
                ),
                confidence=Confidence(str(item["confidence"])),
                evidence=str(item["evidence"]),
                exclusion_reason=str(item.get("exclusion_reason", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError(f"invalid fields[{index}]: {exc}") from exc
        field.validate()
        if field.name in names:
            raise WorkspaceError(f"duplicate battle-context field: {field.name}")
        names.add(field.name)
        fields.append(field)
    return tuple(sorted(fields, key=lambda item: item.name))


def confirmed_hook_context(
    fields: tuple[BattleContextField, ...],
) -> tuple[BattleContextField, ...]:
    return tuple(field for field in fields if field.hook_ready)


def context_report(fields: tuple[BattleContextField, ...]) -> dict[str, object]:
    included = confirmed_hook_context(fields)
    included_names = {field.name for field in included}
    return {
        "format_version": 1,
        "included": [asdict(field) for field in included],
        "excluded": [
            asdict(field)
            | {
                "reason": field.exclusion_reason
                or "field is not confirmed, hook-safe, initialized, and reset-documented"
            }
            for field in fields
            if field.name not in included_names
        ],
    }
