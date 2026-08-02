from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
from typing import Any

from bakugan_ds.errors import WorkspaceError
from bakugan_ds.workspace.manifest import write_json_atomic


def load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"cannot load Gate evidence {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceError(f"Gate evidence {path} must contain a JSON object")
    return payload


def _normalizable_payload(payload: object) -> Any:
    if is_dataclass(payload) and not isinstance(payload, type):
        return asdict(payload)
    return payload


def write_evidence(path: Path, payload: object) -> None:
    normalized = _normalizable_payload(payload)
    if not isinstance(normalized, dict):
        raise WorkspaceError("Gate evidence payload must be a JSON object")
    try:
        write_json_atomic(path, normalized)
    except (OSError, TypeError, ValueError) as exc:
        raise WorkspaceError(f"cannot write Gate evidence {path}: {exc}") from exc
